# chatbot/tools.py

import json
import inspect
from django.db.models import Q
from .models import (
    Account,
    Transaction,
    CreditCard,
    CreditCardSettings,
    DebitCardSettings,
    ChatbotKnowledge,
)

# ==============================================================================
# === HELPER FUNCTION TO DESCRIBE TOOLS FOR THE LLM ============================
# ==============================================================================

def get_tool_descriptions():
    """
    Inspects all tool functions in this module and returns their
    descriptions in a structured format for the LLM.
    """
    tools = [
        get_user_accounts, get_account_balance, list_recent_transactions,
        get_credit_card_details, block_credit_card, update_card_transaction_limits,
        toggle_international_transactions, search_financial_playbook
    ]
    
    tool_specs = []
    for func in tools:
        spec = {
            "name": func.__name__,
            "description": inspect.getdoc(func),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        sig = inspect.signature(func)
        for name, param in sig.parameters.items():
            param_type = "string" # Default type
            if param.annotation == int or param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            
            spec["parameters"]["properties"][name] = {
                "type": param_type,
                "description": f"Parameter for {name}" # Basic description
            }
            if param.default is inspect.Parameter.empty:
                spec["parameters"]["required"].append(name)
        tool_specs.append(spec)
    
    return json.dumps(tool_specs, indent=2)

def get_tool_by_name(name):
    """Returns the actual tool function object from its name string."""
    tools = {
        "get_user_accounts": get_user_accounts,
        "get_account_balance": get_account_balance,
        "list_recent_transactions": list_recent_transactions,
        "get_credit_card_details": get_credit_card_details,
        "block_credit_card": block_credit_card,
        "update_card_transaction_limits": update_card_transaction_limits,
        "toggle_international_transactions": toggle_international_transactions,
        "search_financial_playbook": search_financial_playbook
    }
    return tools.get(name)


# ==============================================================================
# === TOOLS (Functionality unchanged, CrewAI decorators removed) ===============
# ==============================================================================

# --- Category 1: Read-Only Data Retrieval Tools ---

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

def get_account_balance(account_number: str) -> str:
    """
    Use this tool to get the current balance for a specific bank account number.
    """
    try:
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

def block_credit_card(credit_card_number_last_4_digits: str, reason: str) -> str:
    """
    Use this tool to permanently block a user's credit card for security reasons,
    like if it was lost or stolen. Always ask for user confirmation before using.
    """
    try:
        card = CreditCard.objects.filter(card_number__endswith=credit_card_number_last_4_digits).first()
        if card:
            card.status = 'blocked'
            card.save()
            return f"Success: The credit card ending in {credit_card_number_last_4_digits} has been permanently blocked due to: {reason}. A new card will be issued."
        else:
            return f"Credit card ending in {credit_card_number_last_4_digits} not found."
    except Exception as e:
        return f"Error blocking credit card: {e}"

def update_card_transaction_limits(card_number_last_4_digits: str, limit_type: str, new_amount: float) -> str:
    """
    Use this tool to update daily transaction limits on a debit or credit card.
    Valid limit_type values are 'daily_limit', 'daily_pos_limit', or 'daily_international_limit'.
    """
    try:
        card_settings = CreditCardSettings.objects.filter(card__card_number__endswith=card_number_last_4_digits).first()
        card_type = "Credit Card"
        if not card_settings:
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

def toggle_international_transactions(card_number_last_4_digits: str, enabled: bool) -> str:
    """
    Use this tool to enable or disable international transactions on a debit or credit card.
    """
    try:
        card_settings = CreditCardSettings.objects.filter(card__card_number__endswith=card_number_last_4_digits).first()
        card_type = "Credit Card"
        if not card_settings:
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

def search_financial_playbook(query: str) -> str:
    """
    Use this tool to search the bank's internal financial playbook for official advice
    on topics like saving, investment, debt management, and retirement.
    """
    try:
        knowledge_entries = ChatbotKnowledge.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).distinct()

        if not knowledge_entries:
            return f"No relevant information found in the financial playbook for '{query}'."

        results = []
        for entry in knowledge_entries:
            results.append(f"Title: {entry.title}\nContent: {entry.knowledge_text}\n---\n")
        return "".join(results)
    except Exception as e:
        return f"Error searching financial playbook: {e}"