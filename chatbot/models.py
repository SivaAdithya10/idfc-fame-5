from django.db import models
from django.contrib.auth.models import User # Import Django's built-in User model

class UserProfile(models.Model):
    # user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, default="Rohan") # Default for now, will be updated by actual user data
    mobile = models.CharField(max_length=15, blank=True, null=True)
    customer_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.first_name

class InitialBotMessage(models.Model):
    content = models.TextField()

    def __str__(self):
        return "Initial Bot Message"

    class Meta:
        verbose_name_plural = "Initial Bot Message"

class AIModel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)

    def __str__(self):
        return self.display_name

class SuggestedPrompt(models.Model):
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text

class ChatbotKnowledge(models.Model):
    knowledge_text = models.TextField()

    def __str__(self):
        return "Chatbot Knowledge Base"

    class Meta:
        verbose_name_plural = "Chatbot Knowledge Base"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('info', 'Info'),
    )
    type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification - {self.message[:50]}"

    class Meta:
        ordering = ['-timestamp']

class QuickStat(models.Model):
    TREND_CHOICES = (
        ('up', 'Up'),
        ('down', 'Down'),
        ('neutral', 'Neutral'),
    )
    title = models.CharField(max_length=100)
    value = models.CharField(max_length=100) # Storing as CharField to accommodate "₹45,680", "2 loans", "98/100"
    change = models.CharField(max_length=100)
    trend = models.CharField(max_length=10, choices=TREND_CHOICES)
    icon = models.CharField(max_length=50) # To store icon name like "TrendingUp"

    def __str__(self):
        return f"QuickStat - {self.title}"

    class Meta:
        verbose_name_plural = "Quick Stats"

class Account(models.Model):
    ACCOUNT_TYPES = (
        ('Savings Account', 'Savings Account'),
        ('Current Account', 'Current Account'),
        ('Loan Account', 'Loan Account'),
        ('Fixed Deposit Account', 'Fixed Deposit Account'),
    )
    
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES)
    account_number = models.CharField(max_length=20) # Masked or full
    balance = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=5, default="₹")
    status = models.CharField(max_length=20, default="Active")
    branch = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.account_type} ({self.account_number})"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('debit', 'debit'),
        ('credit', 'credit'),
    )
    METHOD_CHOICES = (
        ('UPI', 'UPI'),
        ('Card', 'Card'),
        ('Netbanking', 'Netbanking'),
        ('NEFT', 'NEFT'),
        ('RTGS', 'RTGS'),
    )
    CATEGORY_CHOICES = (
        ('Food', 'Food'),
        ('Shopping', 'Shopping'),
        ('Travel', 'Travel'),
        ('Bills', 'Bills'),
        ('Income', 'Income'),
    )
    date = models.DateField()
    merchant = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES) # Modified to use choices
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)

    def __str__(self):
        return f"Transaction - {self.merchant} ({self.amount})"

    class Meta:
        ordering = ['-date']

class CreditCard(models.Model):
    name = models.CharField(max_length=255)
    card_number = models.CharField(max_length=20) # Masked
    outstanding_balance = models.DecimalField(max_digits=15, decimal_places=2)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2)
    due_date = models.DateField()
    minimum_due = models.DecimalField(max_digits=15, decimal_places=2)
    reward_points = models.IntegerField()

    def __str__(self):
        return f"CreditCard - {self.name}"

    class Meta:
        verbose_name_plural = "Credit Cards"

class ChatMessage(models.Model):
    MESSAGE_TYPES = (
        ('user', 'User'),
        ('bot', 'Bot'),
    )
    session_id = models.CharField(max_length=255, db_index=True) # To group messages into a conversation
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ai_model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, blank=True) # Which AI model was used

    def __str__(self):
        return f"ChatMessage - {self.message_type} - {self.content[:50]}"

    class Meta:
        ordering = ['timestamp']

class UserNotificationSettings(models.Model):
    sms_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    transaction_alerts_enabled = models.BooleanField(default=True)
    bill_reminders_enabled = models.BooleanField(default=True)
    promotions_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification Settings"

class UserSecuritySettings(models.Model):
    two_factor_enabled = models.BooleanField(default=False)
    biometric_enabled = models.BooleanField(default=False)
    session_timeout_minutes = models.IntegerField(default=15)
    login_alerts_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"Security Settings"

class Instruction(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    order = models.IntegerField(unique=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title
