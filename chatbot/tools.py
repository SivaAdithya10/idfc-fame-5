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
        get_card_details, update_card_transaction_limits,
        toggle_international_transactions
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
        "get_card_details": get_card_details,
        "update_card_transaction_limits": update_card_transaction_limits,
        "toggle_international_transactions": toggle_international_transactions
    }
    return tools.get(name)


# ==============================================================================
# === TOOLS ===============
# ==============================================================================

# --- Category 1: Read-Only Data Retrieval Tools ---

def get_user_accounts() -> str:
    """
    Use this tool to get a list of all bank accounts (Savings, Current, Loan account etc.)
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
    Use this tool to get the balance for a specific bank account number. (This could be loan balance, savings balance etc)
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

def list_recent_transactions(limit: int = 10) -> str:
    """
    Use this tool to list the most recent transactions for a given account number.
    You can specify how many transactions to retrieve.
    """
    try:
        transactions = Transaction.objects.order_by('-date')[:limit]
        if not transactions:
            return f"No recent transactions found for your account."

        transaction_details = []
        for t in transactions:
            transaction_details.append(
                f"Date: {t.date.strftime('%Y-%m-%d')}, Merchant: {t.merchant}, Amount: {t.transaction_type}₹{t.amount:,.2f}"
            )
        return f"Recent transactions for your account are: " + "; ".join(transaction_details)
    except Exception as e:
        return f"Error listing recent transactions: {e}"

def get_card_details(card_type: str) -> str:
    """
    Use this tool to get details for a credit or debit card.
    Specify 'credit' or 'debit' for the card_type.
    """
    try:
        if card_type.lower() == 'credit':
            card = CreditCard.objects.first()
            if card:
                return (
                    f"Card: ...{str(card.card_number)[-4:]}, Outstanding: ₹{card.outstanding_balance:,.2f}, "
                    f"Limit: ₹{card.credit_limit:,.2f}, Due Date: {card.due_date.strftime('%Y-%m-%d')}, Reward Points: {card.reward_points}, Credit Score: 750"
                )
            else:
                return "You don't have a Credit card."
        elif card_type.lower() == 'debit':
            settings = DebitCardSettings.objects.first()
            if settings and hasattr(settings, 'card') and settings.card:
                 return (
                    f"Debit Card: ...{str(settings.card.card_number)[-4:]}, "
                    f"Daily Limit: ₹{settings.daily_limit:,.2f}, "
                    f"Daily POS Limit: ₹{settings.daily_pos_limit:,.2f}, "
                    f"International Transactions: {'Enabled' if settings.international_transactions_enabled else 'Disabled'}"
                )
            else:
                return "You don't have a Debit card or its details are not available."
        else:
            return "Invalid card_type. Please specify 'credit' or 'debit'."
    except Exception as e:
        return f"Error retrieving card details: {e}"

# --- Category 2: Security & Action Tools ---

def update_card_transaction_limits(card_type: str, limit_type: str, new_amount: float) -> str:
    """
    Use this tool to update daily transaction limits on a debit or credit card.
    Valid card_type values are 'credit' or 'debit'.
    Valid limit_type values are 'daily_limit', 'daily_pos_limit', or 'daily_international_limit'.
    """
    try:
        card_settings = None
        card_type_str = ""
        card_number_last_4 = ""

        if card_type.lower() == 'credit':
            card_settings = CreditCardSettings.objects.first()
            if card_settings and hasattr(card_settings, 'card') and card_settings.card:
                card_type_str = "Credit Card"
                card_number_last_4 = str(card_settings.card.card_number)[-4:]
        elif card_type.lower() == 'debit':
            card_settings = DebitCardSettings.objects.first()
            if card_settings and hasattr(card_settings, 'card') and card_settings.card:
                card_type_str = "Debit Card"
                card_number_last_4 = str(card_settings.card.card_number)[-4:]
        else:
            return "Invalid card type specified. Please use 'credit' or 'debit'."

        if not card_settings:
            return f"No {card_type} card found."

        if hasattr(card_settings, limit_type):
            setattr(card_settings, limit_type, new_amount)
            card_settings.save()
            return f"Success: The {limit_type} for {card_type_str} ...{card_number_last_4} has been updated to ₹{new_amount:,.2f}."
        else:
            return f"Invalid limit type: {limit_type}. Valid types are 'daily_limit', 'daily_pos_limit', or 'daily_international_limit'."
    except Exception as e:
        return f"Error updating card transaction limits: {e}"

def toggle_international_transactions(card_type: str, enabled: bool) -> str:
    """
    Use this tool to enable or disable international transactions on a debit or credit card.
    Valid card_type values are 'credit' or 'debit'.
    """
    try:
        card_settings = None
        card_type_str = ""
        card_number_last_4 = ""

        if card_type.lower() == 'credit':
            card_settings = CreditCardSettings.objects.first()
            if card_settings and hasattr(card_settings, 'card') and card_settings.card:
                card_type_str = "Credit Card"
                card_number_last_4 = str(card_settings.card.card_number)[-4:]
        elif card_type.lower() == 'debit':
            card_settings = DebitCardSettings.objects.first()
            if card_settings and hasattr(card_settings, 'card') and card_settings.card:
                card_type_str = "Debit Card"
                card_number_last_4 = str(card_settings.card.card_number)[-4:]
        else:
            return "Invalid card type specified. Please use 'credit' or 'debit'."

        if not card_settings:
            return f"No {card_type} card found."

        if hasattr(card_settings, 'international_transactions_enabled'):
            card_settings.international_transactions_enabled = enabled
            card_settings.save()
            status = "enabled" if enabled else "disabled"
            return f"Success: International transactions for {card_type_str} ...{card_number_last_4} are now {status}."
        else:
            return f"International transaction setting not available for card ending in {card_number_last_4}."
    except Exception as e:
        return f"Error toggling international transactions: {e}"

# # --- Category 3: Knowledge & Advice Tools ---

def search_financial_playbook():
    """
    Use this tool to offer financial advice or help user with financial planning.
    Always call this tool before giving any financial advice.
    """
    try:
        knowledge_entries = ChatbotKnowledge.objects.filter(
            Q(title__icontains="Finance Advisory Playbook")).distinct()

        if not knowledge_entries:
            return f"No relevant information found in my knowledge."

        results = []
        for entry in knowledge_entries:
            results.append(f"Title: {entry.title} Content: {entry.knowledge_text} ---")
        return "".join(results)
    except Exception as e:
        return f"Error searching financial playbook: {e}"
