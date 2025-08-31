import logging
from rest_framework import serializers
from .models import (
    UserProfile, InitialBotMessage, AIModel, SuggestedPrompt,
    ChatbotKnowledge, Notification, QuickStat, Account,
    Transaction, CreditCard, ChatMessage, UserNotificationSettings,
    UserSecuritySettings, Instruction
)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'

class InitialBotMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InitialBotMessage
        fields = '__all__'

class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = '__all__'

class SuggestedPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestedPrompt
        fields = '__all__'

class ChatbotKnowledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotKnowledge
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class QuickStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickStat
        fields = '__all__'

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

    def is_valid(self, raise_exception=False):
        valid = super().is_valid(raise_exception=raise_exception)
        if not valid:
            logger = logging.getLogger(__name__)
            logger.error(f"TransactionSerializer validation errors: {self.errors}")
        return valid

class CreditCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditCard
        fields = '__all__'

class ChatMessageSerializer(serializers.ModelSerializer):
    ai_model = AIModelSerializer(read_only=True) # Nested serializer for AIModel
    class Meta:
        model = ChatMessage
        fields = '__all__'

class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationSettings
        fields = '__all__'

class UserSecuritySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSecuritySettings
        fields = '__all__'

class InstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instruction
        fields = '__all__'
