from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from django.conf import settings
from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
import logging
import os

# --- Model and Serializer Imports ---
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

# --- Importing tools ---
from .tools import (
    get_user_accounts,
    get_account_balance,
    list_recent_transactions,
    get_credit_card_details,
    block_credit_card,
    update_card_transaction_limits,
    toggle_international_transactions,
    search_financial_playbook
)

logger = logging.getLogger(__name__)

# ==============================================================================
# === UPDATED CHATBOT VIEW WITH MULTI-AGENT CREW ===============================
# ==============================================================================

@method_decorator(csrf_exempt, name='dispatch')
class ChatView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

    def post(self, request, *args, **kwargs):
        user_message = request.data.get('message')
        history = request.data.get('history', [])
        selected_model = request.data.get('model', 'gemini-2.5-flash') # Default to a modern model

        if not user_message:
            return Response({"error": "No message provided"}, status=status.HTTP_400_BAD_REQUEST)

        gemini_api_key = settings.GEMINI_API_KEY
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY is not set.")
            return Response({"error": "Gemini API key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            knowledge_titles = ["General", "Product Data", "Finance Advisory Playbook"]
            knowledge_records = ChatbotKnowledge.objects.filter(title__in=knowledge_titles)
            backstory_map = {record.title: record.knowledge_text for record in knowledge_records}
        except Exception as e:
            logger.error(f"Failed to fetch chatbot knowledge from DB: {e}")
            backstory_map = {} # Use an empty map to fall back to defaults

        # --- 1. LLM Configuration ---
        # Default LLM for most agents, based on user selection
        llm_user_selected = LLM(
            model=f"gemini/{selected_model}",
            google_api_key=gemini_api_key
        )
        # A more powerful, hardcoded LLM for the main orchestrator agent
        llm_powerful_orchestrator = LLM(
            model=f"gemini/{selected_model}",
            google_api_key=gemini_api_key
        )

        # --- 2. Agent Definitions ---
        orchestrator_agent = Agent(
            role='Chief Customer Interaction Orchestrator',
            goal='Understand the user\'s primary need, answer simple questions directly, and intelligently delegate complex tasks to the appropriate specialist agent. Also, identify contextual opportunities for cross-selling or financial advice.',
            backstory=backstory_map.get(
                'General', 
                # Fallback backstory
                'You are the highly experienced and perceptive head of customer service for a modern digital bank. You can instantly handle common queries but your real talent lies in listening to the customer\'s situation to know exactly when to transfer them to a data specialist, a security officer, or a product advisor. You are the central intelligence of the support team.'
            ),
            llm=llm_powerful_orchestrator, # Assign the powerful LLM
            allow_delegation=True,
            verbose=True
        )

        account_info_agent = Agent(
            role='Account Data Retrieval Specialist',
            goal='Handle all read-only requests related to a customer\'s accounts.',
            backstory='You are a meticulous and secure data analyst with read-only access to the core banking database. Your sole function is to retrieve customer account information accurately and present it clearly.',
            tools=[get_user_accounts, get_account_balance, list_recent_transactions, get_credit_card_details],
            allow_delegation=False,
            verbose=True
        )

        security_agent = Agent(
            role='Card and Account Security Officer',
            goal='Handle sensitive, non-transfer-related actions that affect the security and state of a user\'s card and account.',
            backstory='You are a dedicated security officer in the bank\'s fraud prevention unit. You are authorised to execute urgent security protocols like blocking cards and updating account details. You operate with precision and require explicit user confirmation for every action.',
            tools=[block_credit_card, update_card_transaction_limits, toggle_international_transactions],
            allow_delegation=False,
            verbose=True
        )

        recommender_agent = Agent(
            role='Personalised Product Recommendation Specialist',
            goal='Analyse the user\'s context and financial snapshot to offer relevant, timely, and personalised product recommendations.',
            backstory=backstory_map.get(
                'Product Data',
                # Fallback backstory
                'You are a smart and insightful product advisor. You don\'t just list products; you understand people\'s life moments. When a customer mentions buying a new car, you\'re ready to suggest the best car loan. Your recommendations are always helpful and never pushy.'
            ),
            tools=[get_user_accounts, list_recent_transactions],
            allow_delegation=False,
            verbose=True
        )
        
        financial_advisor_agent = Agent(
            role='Certified Financial Playbook Advisor',
            goal='Provide sound financial advice to users by strictly adhering to the bank\'s approved internal financial playbook.',
            backstory=backstory_map.get(
                'Finance Advisory Playbook',
                # Fallback backstory
                'You are a certified financial advisor who provides guidance based on a comprehensive, pre-approved financial playbook. You don\'t give speculative opinions; you provide trusted, standardised advice from our experts on topics like saving, managing debt, and investing.'
            ),
            tools=[search_financial_playbook],
            allow_delegation=False,
            verbose=True
        )

        # --- 3. Task Definition ---
        # Format history for context
        formatted_history = "\n".join([f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in history])
        
        # The main task is given to the orchestrator agent
        orchestration_task = Task(
            description=(
                f"Analyze the user's latest message based on the conversation history and delegate the task to the appropriate specialist agent if needed. If it's a simple greeting or question, answer it directly.\n\n"
                f"Conversation History:\n{formatted_history}\n\n"
                f"User's Latest Message: \"{user_message}\""
            ),
            agent=orchestrator_agent,
            expected_output="The final, comprehensive, and user-friendly answer to the user's request. If you delegate, this should be the result from the specialist agent."
        )

        # --- 4. Crew Assembly and Execution ---
        try:
            logger.info(f"Kicking off multi-agent crew for user message: {user_message}")
            
            crew = Crew(
                agents=[
                    orchestrator_agent,
                    account_info_agent,
                    security_agent,
                    recommender_agent,
                    financial_advisor_agent
                ],
                tasks=[orchestration_task],
                process=Process.hierarchical,
                manager_llm=llm_powerful_orchestrator,
                llm=llm_user_selected,
                verbose=True
            )

            result = crew.kickoff()
            # The result from a crew kickoff can be a string or a CrewOutput object.
            # We check for a 'raw' attribute to get the string output.
            if hasattr(result, 'raw') and isinstance(result.raw, str):
                bot_response = result.raw
            else:
                bot_response = str(result)
            
            logger.info(f"CrewAI kickoff successful. Response: {bot_response[:100]}...")

        except Exception as e:
            logger.exception(f"Error during CrewAI kickoff for user message: {user_message}")
            error_message = "I'm sorry, I encountered an issue while processing your request. Our technical team has been notified."
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"response": bot_response}, status=status.HTTP_200_OK)


# ==============================================================================
# === EXISTING MODEL VIEWSETS (Unchanged) ======================================
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