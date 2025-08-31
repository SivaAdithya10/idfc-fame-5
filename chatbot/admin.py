from django.contrib import admin
from .models import (
    UserProfile,
    InitialBotMessage,
    AIModel,
    SuggestedPrompt,
    ChatbotKnowledge,
    Notification,
    QuickStat,
    Account,
    Transaction,
    CreditCard,
    Instruction,
    ChatMessage,
    UserNotificationSettings,
    UserSecuritySettings,
    DebitCardSettings,
    CreditCardSettings
)

admin.site.register(UserProfile)
admin.site.register(InitialBotMessage)
admin.site.register(AIModel)
admin.site.register(SuggestedPrompt)
admin.site.register(ChatbotKnowledge)
admin.site.register(Notification)
admin.site.register(QuickStat)
admin.site.register(Account)
admin.site.register(Transaction)
admin.site.register(CreditCard)
admin.site.register(Instruction)
admin.site.register(ChatMessage)
admin.site.register(UserNotificationSettings)
admin.site.register(UserSecuritySettings)
admin.site.register(DebitCardSettings)
admin.site.register(CreditCardSettings)