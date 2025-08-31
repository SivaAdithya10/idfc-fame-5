# chatbot/tools.py

from crewai.tools import tool
from .models import (
    Account,
    Transaction,
    CreditCard,
    CreditCardSettings,
    DebitCardSettings,
    UserSecuritySettings,
    ChatbotKnowledge,
)
from django.db.models import Q

# --- Category 1: Read-Only Data Retrieval Tools ---

@tool("Get User Accounts")
def get_user_accounts() -> str:
    """
    Use this tool to get a list of all bank accounts (Savings, Current, etc.)
    associated with the customer.
    """
    accounts = Account.objects.all()
    if not accounts:
        return "No accounts found for the customer."

    account_details = []
    for account in accounts:
        account_details.append(
            f"{account.account_type}: ...{str(account.account_number)[-4:]}, Balance: ₹{account.balance:,.2f}"
        )
    return "Accounts: " + "; ".join(account_details)

@tool("Get Account Balance")
def get_account_balance(account_number: str) -> str:
    """
    Use this tool to get the current balance for a specific bank account number.
    """
    try:
        # Assuming account_number can be matched by full number or last 4 digits
        account = Account.objects.filter(
            Q(account_number__icontains=account_number) |
            Q(account_number__endswith=account_number)
        ).first()
        if account:
            return f"The balance for account ...{str(account.account_number)[-4:]} is ₹{account.balance:,.2f}."
        else:
            return f"Account ending in {account_number} not found."
    except Exception as e:
        return f"Error retrieving account balance: {e}"

@tool("List Recent Transactions")
def list_recent_transactions(account_number: str, limit: int = 10) -> str:
    """
    Use this tool to list the most recent transactions for a given account number.
    You can specify how many transactions to retrieve.
    """
    try:
        account = Account.objects.filter(
            Q(account_number__icontains=account_number) |
            Q(account_number__endswith=account_number)
        ).first()
        if not account:
            return f"Account ending in {account_number} not found."

        transactions = Transaction.objects.filter(account=account).order_by('-date')[:limit]
        if not transactions:
            return f"No recent transactions found for account ...{str(account.account_number)[-4:]}."

        transaction_details = []
        for t in transactions:
            transaction_details.append(
                f"Date: {t.date.strftime('%Y-%m-%d')}, Merchant: {t.merchant}, Amount: {t.transaction_type}₹{t.amount:,.2f}"
            )
        return f"Recent transactions for account ...{str(account.account_number)[-4:]}: " + "; ".join(transaction_details)
    except Exception as e:
        return f"Error listing recent transactions: {e}"

@tool("Get Credit Card Details")
def get_credit_card_details(credit_card_number_last_4_digits: str) -> str:
    """
    Use this tool to get details like outstanding balance, credit limit, and due date
    for a credit card using the last 4 digits.
    """
    try:
        card = CreditCard.objects.filter(card_number__endswith=credit_card_number_last_4_digits).first()
        if card:
            return (
                f"Card: ...{str(card.card_number)[-4:]}, Outstanding: ₹{card.outstanding_balance:,.2f}, "
                f"Limit: ₹{card.credit_limit:,.2f}, Due Date: {card.due_date.strftime('%Y-%m-%d')}"
            )
        else:
            return f"Credit card ending in {credit_card_number_last_4_digits} not found."
    except Exception as e:
        return f"Error retrieving credit card details: {e}"

# --- Category 2: Security & Action Tools ---

@tool("Block Credit Card")
def block_credit_card(credit_card_number_last_4_digits: str, reason: str) -> str:
    """
    Use this tool to permanently block a user's credit card for security reasons,
    like if it was lost or stolen. Always ask for user confirmation before using.
    """
    try:
        card = CreditCard.objects.filter(card_number__endswith=credit_card_number_last_4_digits).first()
        if card:
            card.status = 'blocked'  # Assuming a 'status' field exists in CreditCard model
            card.save()
            return f"Success: The credit card ending in {credit_card_number_last_4_digits} has been permanently blocked due to: {reason}. A new card will be issued."
        else:
            return f"Credit card ending in {credit_card_number_last_4_digits} not found."
    except Exception as e:
        return f"Error blocking credit card: {e}"

@tool("Update Card Transaction Limits")
def update_card_transaction_limits(card_number_last_4_digits: str, limit_type: str, new_amount: float) -> str:
    """
    Use this tool to update daily transaction limits on a debit or credit card.
    Valid limit_type values are 'daily_limit', 'daily_pos_limit', or 'daily_international_limit'.
    """
    try:
        # Try to find in CreditCardSettings first
        card_settings = CreditCardSettings.objects.filter(card__card_number__endswith=card_number_last_4_digits).first()
        card_type = "Credit Card"
        if not card_settings:
            # If not found, try DebitCardSettings
            card_settings = DebitCardSettings.objects.filter(card__card_number__endswith=card_number_last_4_digits).first()
            card_type = "Debit Card"

        if not card_settings:
            return f"Card settings for card ending in {card_number_last_4_digits} not found."

        if hasattr(card_settings, limit_type):
            setattr(card_settings, limit_type, new_amount)
            card_settings.save()
            return f"Success: The {limit_type} for {card_type} ...{card_number_last_4_digits} has been updated to ₹{new_amount:,.2f}."
        else:
            return f"Invalid limit type: {limit_type}. Valid types are 'daily_limit', 'daily_pos_limit', or 'daily_international_limit'."
    except Exception as e:
        return f"Error updating card transaction limits: {e}"

@tool("Toggle International Transactions")
def toggle_international_transactions(card_number_last_4_digits: str, enabled: bool) -> str:
    """
    Use this tool to enable or disable international transactions on a debit or credit card.
    """
    try:
        # Try to find in CreditCardSettings first
        card_settings = CreditCardSettings.objects.filter(card__card_number__endswith=card_number_last_4_digits).first()
        card_type = "Credit Card"
        if not card_settings:
            # If not found, try DebitCardSettings
            card_settings = DebitCardSettings.objects.filter(card__card_number__endswith=card_number_last_4_digits).first()
            card_type = "Debit Card"

        if not card_settings:
            return f"Card settings for card ending in {card_number_last_4_digits} not found."

        if hasattr(card_settings, 'international_transactions_enabled'):
            card_settings.international_transactions_enabled = enabled
            card_settings.save()
            status = "enabled" if enabled else "disabled"
            return f"Success: International transactions for {card_type} ...{card_number_last_4_digits} are now {status}."
        else:
            return f"International transaction setting not available for card ending in {card_number_last_4_digits}."
    except Exception as e:
        return f"Error toggling international transactions: {e}"

# --- Category 3: Knowledge & Advice Tools ---

@tool("Search Financial Playbook")
def search_financial_playbook(query: str) -> str:
    """
    Use this tool to search the bank's internal financial playbook for official advice
    on topics like saving, investment, debt management, and retirement.
    """
    try:
        # Perform a simple keyword search in the content of ChatbotKnowledge entries
        knowledge_entries = ChatbotKnowledge.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).distinct()

        if not knowledge_entries:
            return f"No relevant information found in the financial playbook for '{query}'."

        results = []
        for entry in knowledge_entries:
            results.append(f"""Title: {entry.title}
            Content: {entry.knowledge_text}
            " + "
            ---
            """)
        results.join(results)
        return results
    except Exception as e:
        return f"Error searching financial playbook: {e}"


