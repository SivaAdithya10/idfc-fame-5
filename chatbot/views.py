# chatbot/views.py

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from django.conf import settings
import logging
import os
import json
import uuid # Used for creating a unique request ID for tracing
import time

# --- NEW: Import for Google Gemini API ---
import google.generativeai as genai

# --- Import for Email Utility ---
from .email_utils import send_chat_notification_email

# --- Model and Serializer Imports (Unchanged) ---
from .models import (
    UserProfile, InitialBotMessage, AIModel, SuggestedPrompt,
    ChatbotKnowledge, Notification, QuickStat, Account,
    Transaction, CreditCard, ChatMessage, UserNotificationSettings,
    UserSecuritySettings, Instruction, DebitCardSettings, CreditCardSettings
)
from .serializers import (
    UserProfileSerializer, InitialBotMessageSerializer, AIModelSerializer, SuggestedPromptSerializer,
    ChatbotKnowledgeSerializer, NotificationSerializer, QuickStatSerializer, AccountSerializer,
    TransactionSerializer, CreditCardSerializer, ChatMessageSerializer, UserNotificationSettingsSerializer,
    UserSecuritySettingsSerializer, InstructionSerializer, DebitCardSettingsSerializer, CreditCardSettingsSerializer
)

# --- Importing tools (now with new structure) ---
from .tools import get_tool_descriptions_for_agent, get_tool_by_name

logger = logging.getLogger(__name__)

# ==============================================================================
# === UPDATED CHATBOT VIEW WITH MULTI-AGENT ARCHITECTURE =======================
# ==============================================================================

@method_decorator(csrf_exempt, name='dispatch')
class ChatView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

    def post(self, request, *args, **kwargs):
        request_id = uuid.uuid4()
        user_message = None
        history = []
        selected_model = 'gemini-1.5-flash'
        original_user_input_type = None # New variable to track input type

        # --- Determine Input Type: Audio or Text (This part is unchanged) ---
        if 'audio' in request.FILES:
            original_user_input_type = 'audio'
            logger.info(f"======== [START AUDIO REQUEST: {request_id}] ========")
            audio_file = request.FILES['audio']
            history = json.loads(request.data.get('history', '[]'))
            selected_model = request.data.get('model', 'gemini-1.5-flash')
            logger.info(f"[{request_id}] Received audio file: {audio_file.name}")

            gemini_api_key = settings.GEMINI_API_KEY
            if not gemini_api_key:
                return Response({"error": "Gemini API key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                genai.configure(api_key=gemini_api_key)
                temp_dir = os.path.join(settings.BASE_DIR, 'temp_audio')
                os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, f"{request_id}_{audio_file.name}")

                with open(temp_path, 'wb+') as temp_f:
                    for chunk in audio_file.chunks():
                        temp_f.write(chunk)

                uploaded_file = genai.upload_file(path=temp_path)
                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(2) # Reduced sleep time
                    uploaded_file = genai.get_file(uploaded_file.name)

                if uploaded_file.state.name != "ACTIVE":
                    logger.error(f"[{request_id}] File {uploaded_file.name} is not in an ACTIVE state. Current state: {uploaded_file.state.name}")
                    return Response({"error": "Failed to process audio file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                os.remove(temp_path)

                model = genai.GenerativeModel(selected_model)
                transcription_prompt = "Please transcribe this audio file. Only return the transcribed text."
                transcription_response = model.generate_content([transcription_prompt, uploaded_file])
                user_message = transcription_response.text.strip()
                logger.info(f"[{request_id}] Transcribed from audio: '{user_message}'")

            except Exception as e:
                logger.exception(f"[{request_id}] Error during audio processing.")
                # Even if audio processing fails, we still want to send a notification
                # with the original input type noted.
                user_message = "Audio transcription failed." # Set a default message for email
                # Do not return here, allow the email to be sent before returning error response
        else:
            # --- TEXT PATH ---
            original_user_input_type = 'text'
            logger.info(f"======== [START TEXT REQUEST: {request_id}] ========")
            user_message = request.data.get('message')
            history = request.data.get('history', [])
            selected_model = request.data.get('model', 'gemini-1.5-flash')

        logger.info(f"[{request_id}] User Message (after potential transcription): '{user_message}'")

        if not user_message:
            return Response({"error": "No message provided"}, status=status.HTTP_400_BAD_REQUEST)

        gemini_api_key = settings.GEMINI_API_KEY
        if not gemini_api_key:
            logger.error(f"[{request_id}] GEMINI_API_KEY is not set.")
            return Response({"error": "Gemini API key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # --- 1. Configure Gemini API ---
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel(selected_model)

            # --- 2. STEP 1: ORCHESTRATION ---
            # The first LLM call decides which specialist agent to route the query to.
            formatted_history = "\n".join([f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in history])

            orchestrator_prompt = f"""
You are the master request orchestrator for a digital bank. Your primary job is to analyze the user's query and route it to the correct specialist agent. Do not attempt to answer the user yourself.

Here are the available specialist agents and their responsibilities:
- **AccountSpecialist**: Use for any questions about retrieving data. This includes checking account balances, listing transactions, fetching account numbers, or getting details about credit/debit cards.
- **SecurityOfficer**: Use for any requests that involve an action or a change to security settings. This includes updating transaction limits or enabling/disabling international transactions.
- **FinancialAdvisor**: Use for any questions related to financial advice, planning, investment options, or market trends.
- **Generalist**: Use for simple greetings, farewells, non-financial questions, or if the user's intent is unclear and doesn't fit any other specialist.

**Conversation History:**
{formatted_history}

**User's Latest Message:**
"{user_message}"

Based on the user's latest message, which specialist agent is the most appropriate to handle the request?
Respond with ONLY a JSON object in the following format. Do not add any other text.
{{
  "agent_name": "<name_of_the_chosen_agent>"
}}
"""
            logger.info(f"[{request_id}] STEP 1: Performing orchestration call to select an agent...")
            orchestrator_response = model.generate_content(orchestrator_prompt)

            try:
                decision_text = orchestrator_response.text.strip().replace("```json", "").replace("```", "")
                decision_json = json.loads(decision_text)
                chosen_agent = decision_json.get("agent_name")
                logger.info(f"[{request_id}] Orchestrator selected agent: '{chosen_agent}'")
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"[{request_id}] Failed to parse orchestrator JSON response: {e}. Raw response: {orchestrator_response.text}")
                # Fallback to a general response if orchestration fails
                return Response({"response": "I'm having trouble understanding your request. Could you please rephrase it?"}, status=status.HTTP_200_OK)

            bot_response = ""
            tool_result = None
            # Variables for email notification
            main_agent_decision = None
            sub_agent_used_for_email = None
            tools_used_for_email = None
            sub_agent_raw_response = None
            final_bot_output = None

            # --- 3. STEP 2: DELEGATION TO SUB-AGENT ---
            if chosen_agent == "Generalist":
                logger.info(f"[{request_id}] Delegating to Generalist for a direct answer.")
                main_agent_decision = "Generalist"
                generalist_prompt = f"""
You are a friendly and helpful banking assistant. The user said: "{user_message}".
Provide a direct, conversational response. Do not offer to perform any actions you can't do.
If you don't know the answer, say so politely.
"""
                final_response = model.generate_content(generalist_prompt)
                bot_response = final_response.text
                final_bot_output = bot_response

            elif chosen_agent in ["AccountSpecialist", "SecurityOfficer", "FinancialAdvisor"]:
                logger.info(f"[{request_id}] Delegating to sub-agent: '{chosen_agent}'")
                main_agent_decision = chosen_agent
                sub_agent_used_for_email = chosen_agent
                tool_descriptions = get_tool_descriptions_for_agent(chosen_agent)

                sub_agent_prompt = f"""
You are a specialist agent known as the '{chosen_agent}'. Your role is to handle specific user requests by using your available tools.
Based on the user's message, decide which tool to call.

**User's Message:**
"{user_message}"

**Your Available Tools:**
{tool_descriptions}

Respond with ONLY a JSON object indicating the tool to call and its arguments.
If no tool is appropriate, respond with a JSON object containing an error.
{{
  "tool_name": "<name_of_the_tool_to_call>",
  "arguments": {{
    "arg1_name": "value1",
    "arg2_name": "value2"
  }}
}}"""
                logger.info(f"[{request_id}] STEP 2a: Sub-agent '{chosen_agent}' is deciding which tool to use...")
                sub_agent_response = model.generate_content(sub_agent_prompt)
                sub_agent_raw_response = sub_agent_response.text # Capture raw response

                try:
                    tool_call_text = sub_agent_response.text.strip().replace("```json", "").replace("```", "")
                    tool_call_json = json.loads(tool_call_text)
                    tool_name = tool_call_json.get("tool_name")
                    arguments = tool_call_json.get("arguments", {})

                    if not tool_name:
                         raise ValueError("Sub-agent did not return a tool name.")

                    tools_used_for_email = f"Tool: {tool_name}, Arguments: {arguments}" # Capture tool info

                    logger.info(f"[{request_id}] Sub-agent '{chosen_agent}' decided to use tool '{tool_name}' with arguments: {arguments}")

                    tool_function = get_tool_by_name(tool_name)
                    if not tool_function:
                        logger.error(f"[{request_id}] Sub-agent '{chosen_agent}' chose an unknown tool: {tool_name}")
                        bot_response = "I'm sorry, I tried to perform an action but couldn't find the right internal capability."
                        final_bot_output = bot_response
                    else:
                        tool_result = tool_function(**arguments)
                        logger.info(f"[{request_id}] TOOL OUTPUT (RAW): '{tool_result}'")

                except (json.JSONDecodeError, AttributeError, ValueError) as e:
                    logger.error(f"[{request_id}] Sub-agent '{chosen_agent}' failed to produce a valid tool call or tool execution failed: {e}. Raw response: {sub_agent_response.text}")
                    bot_response = "I'm sorry, I was unable to complete that action. This is demo so my actions are limited. However, I have the capability to perform this if given enough permissions. Until then Please try contacting customer support."
                    final_bot_output = bot_response
                except Exception as e:
                    logger.exception(f"[{request_id}] An unexpected error occurred while executing tool '{tool_name}'.")
                    bot_response = "An unexpected error occurred. Please contact support."
                    final_bot_output = bot_response

            else:
                logger.warning(f"[{request_id}] Orchestrator returned an unknown agent: '{chosen_agent}'")
                main_agent_decision = "Unknown"
                bot_response = "I'm not sure how to handle that request. Please try rephrasing."
                final_bot_output = bot_response

            # --- 4. STEP 3: FINALIZATION (if a tool was used) ---
            if tool_result:
                finalizer_prompt = f"""
The user's original request was: "{user_message}"
An internal specialist agent was used to process this, and it produced the following result:
"{tool_result}"

Based on this result, formulate a final, comprehensive, and user-friendly answer.
- If the result indicates success, confirm the action in a friendly way.
- If the result is data, present it clearly and concisely.
- If the result is an error, apologize and explain it simply.
- Do not mention that you used a "tool", "function", or "agent". Speak naturally as a single, unified banking assistant.
"""
                logger.info(f"[{request_id}] STEP 3: Performing finalization call to format the tool output...")
                final_response = model.generate_content(finalizer_prompt)
                bot_response = final_response.text
                final_bot_output = bot_response # Update final output after finalization
                logger.info(f"[{request_id}] FINALIZER RAW OUTPUT:\n{bot_response}")

            # --- Send Email Notification ---
            try:
                email_user_input_query = user_message
                if original_user_input_type == 'audio':
                    if user_message and user_message != "Audio transcription failed.":
                        email_user_input_query = f"Audio Input (transcribed: {user_message})"
                    else:
                        email_user_input_query = "Audio Input (transcription failed)"

                send_chat_notification_email(
                    user_input_query=email_user_input_query,
                    main_agent_response=main_agent_decision,
                    sub_agent_used=sub_agent_used_for_email,
                    tools_used=tools_used_for_email,
                    sub_agent_response=sub_agent_raw_response,
                    final_output=final_bot_output,
                    chat_history=formatted_history
                )
            except Exception as e:
                logger.error(f"[{request_id}] Error sending email notification: {e}")

            # --- 5. Return Final Response ---
            logger.info(f"[{request_id}] FINAL RESPONSE to User: '{bot_response}'")
            logger.info(f"======== [END REQUEST: {request_id}] ========\n")
            return Response({"response": bot_response}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"[{request_id}] A critical error occurred in ChatView for message: {user_message}")
            error_message = "I'm sorry, a critical error occurred. Our technical team has been notified."
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==============================================================================
# === ALL OTHER VIEWSETS (UNCHANGED) ===========================================
# ==============================================================================

@method_decorator(csrf_exempt, name='dispatch')
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class InitialBotMessageViewSet(viewsets.ModelViewSet):
    queryset = InitialBotMessage.objects.all()
    serializer_class = InitialBotMessageSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class AIModelViewSet(viewsets.ModelViewSet):
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class SuggestedPromptViewSet(viewsets.ModelViewSet):
    queryset = SuggestedPrompt.objects.all()
    serializer_class = SuggestedPromptSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class ChatbotKnowledgeViewSet(viewsets.ModelViewSet):
    queryset = ChatbotKnowledge.objects.all()
    serializer_class = ChatbotKnowledgeSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class QuickStatViewSet(viewsets.ModelViewSet):
    queryset = QuickStat.objects.all()
    serializer_class = QuickStatSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

    @action(detail=False, methods=['get'])
    def choices(self, request):
        transaction_types = [{'value': choice[0], 'label': choice[1]} for choice in Transaction.TRANSACTION_TYPES]
        method_choices = [{'value': choice[0], 'label': choice[1]} for choice in Transaction.METHOD_CHOICES]
        category_choices = [{'value': choice[0], 'label': choice[1]} for choice in Transaction.CATEGORY_CHOICES]
        return Response({
            'transaction_types': transaction_types,
            'method_choices': method_choices,
            'category_choices': category_choices,
        })

@method_decorator(csrf_exempt, name='dispatch')
class CreditCardViewSet(viewsets.ModelViewSet):
    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class DebitCardSettingsViewSet(viewsets.ModelViewSet):
    queryset = DebitCardSettings.objects.all()
    serializer_class = DebitCardSettingsSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class CreditCardSettingsViewSet(viewsets.ModelViewSet):
    queryset = CreditCardSettings.objects.all()
    serializer_class = CreditCardSettingsSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class UserNotificationSettingsViewSet(viewsets.ModelViewSet):
    queryset = UserNotificationSettings.objects.all()
    serializer_class = UserNotificationSettingsSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class UserSecuritySettingsViewSet(viewsets.ModelViewSet):
    queryset = UserSecuritySettings.objects.all()
    serializer_class = UserSecuritySettingsSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

@method_decorator(csrf_exempt, name='dispatch')
class InstructionViewSet(viewsets.ModelViewSet):
    queryset = Instruction.objects.all()
    serializer_class = InstructionSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True