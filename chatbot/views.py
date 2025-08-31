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

# --- NEW: Import for Google Gemini API ---
import google.generativeai as genai

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

# --- Importing tools (now without CrewAI decorators) ---
from .tools import get_tool_descriptions, get_tool_by_name

logger = logging.getLogger(__name__)

# ==============================================================================
# === ENHANCED LOGGING SETUP ===================================================
# ==============================================================================

# This map helps translate a tool call back to the conceptual "agent" for clearer logs.
TOOL_TO_AGENT_MAP = {
    'get_user_accounts': 'Account Data Retrieval Specialist',
    'get_account_balance': 'Account Data Retrieval Specialist',
    'list_recent_transactions': 'Account Data Retrieval Specialist',
    'get_credit_card_details': 'Account Data Retrieval Specialist',
    'block_credit_card': 'Card and Account Security Officer',
    'update_card_transaction_limits': 'Card and Account Security Officer',
    'toggle_international_transactions': 'Card and Account Security Officer',
    'search_financial_playbook': 'Certified Financial Playbook Advisor'
}


# ==============================================================================
# === UPDATED CHATBOT VIEW WITH PERFECT LOGGING ================================
# ==============================================================================

@method_decorator(csrf_exempt, name='dispatch')
class ChatView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def post(self, request, *args, **kwargs):
        # Generate a unique ID for this request to trace it in the logs
        request_id = uuid.uuid4()
        
        user_message = request.data.get('message')
        history = request.data.get('history', [])
        selected_model = request.data.get('model', 'gemini-1.5-flash')

        logger.info(f"======== [START REQUEST: {request_id}] ========")
        logger.info(f"[{request_id}] User Message: '{user_message}'")

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

            # --- 2. Build the Orchestrator Prompt ---
            formatted_history = "\n".join([f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in history])
            tool_descriptions = get_tool_descriptions()

            orchestrator_prompt = f"""
You are the Chief Customer Interaction Orchestrator for a modern digital bank. Your goal is to understand the user's needs and decide the best course of action.
You have access to a set of tools to help you. Based on the user's message and the conversation history, you must decide what to do.
Your available actions are:
1.  **call_tool**: If the user's request requires fetching data or performing an action, choose the appropriate tool.
2.  **direct_answer**: If the user's message is a simple greeting, a follow-up clarification, or a question that doesn't require a tool, answer it directly.
**Conversation History:**
{formatted_history}
**User's Latest Message:**
"{user_message}"
**Available Tools:**
{tool_descriptions}
**Your Decision:**
Respond with ONLY a JSON object in the following format. Do not add any other text before or after the JSON.
If you decide to call a tool:
{{
  "decision": "call_tool",
  "tool_name": "<name_of_the_tool_to_call>",
  "arguments": {{
    "arg1_name": "value1",
    "arg2_name": "value2"
  }}
}}
If you decide to answer directly:
{{
  "decision": "direct_answer",
  "response": "<your_direct_and_helpful_answer>"
}}
"""
            
            # --- 3. First LLM Call: Orchestration ---
            logger.info(f"[{request_id}] STEP 1: Performing orchestration call to Gemini...")
            orchestrator_response = model.generate_content(orchestrator_prompt)
            
            try:
                decision_text = orchestrator_response.text.strip().replace("```json", "").replace("```", "")
                logger.info(f"[{request_id}] ORCHESTRATOR RAW OUTPUT:\n{decision_text}")
                decision_json = json.loads(decision_text)
                decision = decision_json.get("decision")
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"[{request_id}] Failed to parse orchestrator JSON response: {e}. Raw response was: {orchestrator_response.text}")
                return Response({"response": orchestrator_response.text}, status=status.HTTP_200_OK)

            bot_response = ""

            # --- 4. Execute Decision ---
            if decision == "direct_answer":
                bot_response = decision_json.get("response", "I'm sorry, I could not generate a response.")
                logger.info(f"[{request_id}] Decision: Direct Answer. No agent transfer needed.")

            elif decision == "call_tool":
                tool_name = decision_json.get("tool_name")
                arguments = decision_json.get("arguments", {})
                
                # LOGGING: Log agent transfer and tool usage
                agent_name = TOOL_TO_AGENT_MAP.get(tool_name, "Unknown Agent")
                logger.info(f"[{request_id}] Decision: Delegate to Agent -> '{agent_name}'")
                logger.info(f"[{request_id}] STEP 2: Agent '{agent_name}' is handling the query.")
                logger.info(f"[{request_id}] TOOL USED: '{tool_name}' with arguments: {arguments}")
                
                tool_function = get_tool_by_name(tool_name)

                if not tool_function:
                    logger.error(f"[{request_id}] Orchestrator decided to call an unknown tool: {tool_name}")
                    bot_response = "I'm sorry, I tried to perform an action but couldn't find the right tool."
                else:
                    try:
                        tool_result = tool_function(**arguments)
                        logger.info(f"[{request_id}] TOOL OUTPUT (RAW): '{tool_result}'")

                        # --- 5. Second LLM Call: Finalization ---
                        finalizer_prompt = f"""
The user asked the following question: "{user_message}"
To answer this, I performed an internal action by calling the tool '{tool_name}' and got the following result:
"{tool_result}"
Based on this result, please formulate a final, comprehensive, and user-friendly answer.
- If the result indicates success, confirm the action in a friendly way.
- If the result is data, present it clearly.
- If the result is an error, apologize and explain it simply.
- Do not mention that you used a "tool" or "function". Speak naturally as a banking assistant.
"""
                        logger.info(f"[{request_id}] STEP 3: Performing finalization call to Gemini to format the tool output...")
                        final_response = model.generate_content(finalizer_prompt)
                        bot_response = final_response.text
                        logger.info(f"[{request_id}] FINALIZER RAW OUTPUT:\n{bot_response}")

                    except Exception as e:
                        logger.exception(f"[{request_id}] Error executing tool '{tool_name}' or during finalization call.")
                        bot_response = "I'm sorry, I encountered an error while trying to complete your request."
            
            else:
                 logger.warning(f"[{request_id}] Orchestrator returned an unknown decision: '{decision}'")
                 bot_response = "I'm not sure how to handle that request. Please try rephrasing."

            logger.info(f"[{request_id}] FINAL RESPONSE to User: '{bot_response}'")
            logger.info(f"======== [END REQUEST: {request_id}] ========\n")
            return Response({"response": bot_response}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"[{request_id}] A critical error occurred in ChatView for message: {user_message}")
            error_message = "I'm sorry, a critical error occurred. Our technical team has been notified."
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==============================================================================
# === MODEL VIEWSETS ======================================
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