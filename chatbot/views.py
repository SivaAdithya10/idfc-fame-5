from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from django.views.decorators.csrf import csrf_exempt
from crewai import Agent, Task, Crew, Process
from django.conf import settings
from crewai.llm import LLM
import logging
import os

from .models import (
    UserProfile, InitialBotMessage, AIModel, SuggestedPrompt,
    ChatbotKnowledge, Notification, QuickStat, Account,
    Transaction, CreditCard, ChatMessage, UserNotificationSettings,
    UserSecuritySettings, Instruction
)
from .serializers import (
    UserProfileSerializer, InitialBotMessageSerializer, AIModelSerializer, SuggestedPromptSerializer,
    ChatbotKnowledgeSerializer, NotificationSerializer, QuickStatSerializer, AccountSerializer,
    TransactionSerializer, CreditCardSerializer, ChatMessageSerializer, UserNotificationSettingsSerializer,
    UserSecuritySettingsSerializer, InstructionSerializer
)

logger = logging.getLogger(__name__)

class ChatView(APIView):
    def post(self, request, *args, **kwargs):
        user_message = request.data.get('message')
        history = request.data.get('history', []) 
        selected_model = request.data.get('model', 'gemini-2.5-flash-lite')

        if not user_message:
            logger.warning("ChatView received request with no message.")
            return Response({"error": "No message provided"}, status=status.HTTP_400_BAD_REQUEST)

        gemini_api_key = settings.GEMINI_API_KEY
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY is not set in environment variables.")
            return Response({"error": "Gemini API key not configured."}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            llm = LLM(
                model=f"gemini/{selected_model}",
                google_api_key=gemini_api_key
            )
        except:
            logger.error("Error configuring Gemini LLM.")
            return Response({"error": f"Failed to configure LLM"}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        chatbot_agent = Agent(
            role='Customer Support Chatbot',
            goal='Continue the conversation with the user, providing helpful and concise answers based on the provided history and their latest message.',
            backstory='You are a helpful and friendly AI assistant for customer support, engaged in an ongoing conversation with a user. Your goal is to be natural and conversational.',
            verbose=True,
            allow_delegation=False,
            llm=llm,
        )

        formatted_history = ""
        if history:
            formatted_history = "This is the conversation history so far:\n"
            for message in history:
                role = message.get('role', 'user')
                content = message.get('content', '')
                formatted_history += f"- {role.capitalize()}: {content}\n"
            formatted_history += "\n---\n"
        
        task_description = (
            f"{formatted_history}"
            f"Based on the conversation history above, provide a helpful and concise response to the user's latest message:\n"
            f"\"{user_message}\""
        )
        
        chat_task = Task(
            description=task_description,
            agent=chatbot_agent,
            expected_output="A concise and helpful response that continues the conversation naturally."
        )

        try:
            logger.info(f"Attempting to kickoff CrewAI for user message: {user_message}")
            if history:
                logger.info(f"Conversation history contains {len(history)} messages.")

            crew = Crew(agents=[chatbot_agent], tasks=[chat_task], verbose=True)
            result = crew.kickoff()
            
            bot_response = result.raw
            logger.info(f"CrewAI kickoff successful. Response: {bot_response[:100]}...")

        except Exception as e:
            logger.exception(f"Error during CrewAI kickoff for user message: {user_message}")
            error_message = f"Our engineers are fixing this. Kindly allow us sometime"
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"response": bot_response}, status=status.HTTP_200_OK)


# Model ViewSets
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class InitialBotMessageViewSet(viewsets.ModelViewSet):
    queryset = InitialBotMessage.objects.all()
    serializer_class = InitialBotMessageSerializer

class AIModelViewSet(viewsets.ModelViewSet):
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer

class SuggestedPromptViewSet(viewsets.ModelViewSet):
    queryset = SuggestedPrompt.objects.all()
    serializer_class = SuggestedPromptSerializer

class ChatbotKnowledgeViewSet(viewsets.ModelViewSet):
    queryset = ChatbotKnowledge.objects.all()
    serializer_class = ChatbotKnowledgeSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

class QuickStatViewSet(viewsets.ModelViewSet):
    queryset = QuickStat.objects.all()
    serializer_class = QuickStatSerializer

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    csrf_exempt = True

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.error(f"Transaction creation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

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

class CreditCardViewSet(viewsets.ModelViewSet):
    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer

class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer

class UserNotificationSettingsViewSet(viewsets.ModelViewSet):
    queryset = UserNotificationSettings.objects.all()
    serializer_class = UserNotificationSettingsSerializer

class UserSecuritySettingsViewSet(viewsets.ModelViewSet):
    queryset = UserSecuritySettings.objects.all()
    serializer_class = UserSecuritySettingsSerializer

class InstructionViewSet(viewsets.ModelViewSet):
    queryset = Instruction.objects.all()
    serializer_class = InstructionSerializer

