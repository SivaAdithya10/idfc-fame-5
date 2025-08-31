from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChatView,
    UserProfileViewSet, InitialBotMessageViewSet, AIModelViewSet, SuggestedPromptViewSet,
    ChatbotKnowledgeViewSet, NotificationViewSet, QuickStatViewSet, AccountViewSet,
    TransactionViewSet, CreditCardViewSet, ChatMessageViewSet, UserNotificationSettingsViewSet,
    UserSecuritySettingsViewSet, InstructionViewSet,
    DebitCardSettingsViewSet, CreditCardSettingsViewSet # Added new ViewSets
)

router = DefaultRouter()
router.register(r'userprofiles', UserProfileViewSet)
router.register(r'initialbotmessages', InitialBotMessageViewSet)
router.register(r'aimodels', AIModelViewSet)
router.register(r'suggestedprompts', SuggestedPromptViewSet)
router.register(r'chatbotknowledge', ChatbotKnowledgeViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'quickstats', QuickStatViewSet)
router.register(r'accounts', AccountViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'creditcards', CreditCardViewSet)
router.register(r'chatmessages', ChatMessageViewSet)
router.register(r'usernotificationsettings', UserNotificationSettingsViewSet)
router.register(r'usersecuritysettings', UserSecuritySettingsViewSet)
router.register(r'instructions', InstructionViewSet)
router.register(r'debitcardsettings', DebitCardSettingsViewSet)
router.register(r'creditcardsettings', CreditCardSettingsViewSet)

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('', include(router.urls)),
]