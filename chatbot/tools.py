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
# === INDIVIDUAL TOOLS (Functions are unchanged) ===============================
# ==============================================================================

# --- Category 1: Read-Only Data Retrieval Tools ---

def get_user_accounts() -> str:
    """
    Use this tool to get a list of all bank accounts (Savings, Current, Loan account etc.)
    associated with the customer. This also returns the account balance details.
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

def list_recent_transactions(limit: int = 10) -> str:
    """
    Use this tool to list the most recent transactions.
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
                    f"Limit: ₹{card.credit_limit:,.2f}, Due Date: {card.due_date.strftime('%Y-%m-%d')}, "
                    f"Reward Points: {card.reward_points}, Credit Score: 750"
                )
            else:
                return "You don't have a Credit card."
        elif card_type.lower() == 'debit':
            settings = DebitCardSettings.objects.first()
            # CORRECTED: Check for the '.account' attribute which exists on the model
            if settings and hasattr(settings, 'account') and settings.account:
                 return (
                    # CORRECTED: Use settings.account.account_number for debit card details
                    f"Debit Card linked to account ...{str(settings.account.account_number)[-4:]}, "
                    f"Daily Limit: ₹{settings.daily_limit:,.2f}, "
                    f"Daily POS Limit: ₹{settings.daily_pos_limit:,.2f}, "
                    f"International Transactions: {'Enabled' if settings.enable_international_transaction else 'Disabled'}"
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
            # CORRECTED: Check for the actual attribute '.credit_card'
            if card_settings and hasattr(card_settings, 'credit_card'):
                card_type_str = "Credit Card"
                # ADDED: Get the last 4 digits for the response message
                card_number_last_4 = str(card_settings.credit_card.card_number)[-4:]
        elif card_type.lower() == 'debit':
            card_settings = DebitCardSettings.objects.first()
            # CORRECTED: Check for the actual attribute '.account'
            if card_settings and hasattr(card_settings, 'account'):
                card_type_str = "Debit Card"
                # ADDED: Get the last 4 digits for the response message
                card_number_last_4 = str(card_settings.account.account_number)[-4:]
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
            # CORRECTED: Check for the actual attribute '.credit_card'
            if card_settings and hasattr(card_settings, 'credit_card'):
                card_type_str = "Credit Card"
                # ADDED: Get the last 4 digits for the response message
                card_number_last_4 = str(card_settings.credit_card.card_number)[-4:]
        elif card_type.lower() == 'debit':
            card_settings = DebitCardSettings.objects.first()
            # CORRECTED: Check for the actual attribute '.account'
            if card_settings and hasattr(card_settings, 'account'):
                card_type_str = "Debit Card"
                # ADDED: Get the last 4 digits for the response message
                card_number_last_4 = str(card_settings.account.account_number)[-4:]
        else:
            return "Invalid card type specified. Please use 'credit' or 'debit'."

        if not card_settings:
            return f"No {card_type} card found."

        # CORRECTED: Check for 'enable_international_transaction' to match the model field
        if hasattr(card_settings, 'enable_international_transaction'):
            card_settings.enable_international_transaction = enabled
            card_settings.save()
            status = "enabled" if enabled else "disabled"
            return f"Success: International transactions for {card_type_str} ...{card_number_last_4} is now {status}."
        else:
            return f"International transaction setting not available for the card"
    except Exception as e:
        return f"Error toggling international transactions: {e}"


# --- Category 3: Knowledge & Advice Tools ---

def search_financial_playbook():
    """
    Use this tool to offer financial advice or help user with financial planning.
    Always call this tool before giving any financial advice.
    """
    try:
        knowledge_entries = ChatbotKnowledge.objects.filter(title="Finance Advisory Playbook").distinct()

        if not knowledge_entries:
            return f"No relevant information found in my knowledge base."

        results = []
        for entry in knowledge_entries:
            results.append(f"Title: {entry.title}\nContent: {entry.knowledge_text}\n---")
        return "".join(results)
    except Exception as e:
        return f"Error searching financial playbook: {e}"


# ==============================================================================
# === NEW: AGENT TOOLKIT DEFINITIONS ===========================================
# ==============================================================================

# Define which tools belong to which agent.
ACCOUNT_SPECIALIST_TOOLS = {
    "get_user_accounts": get_user_accounts,
    "list_recent_transactions": list_recent_transactions,
    "get_card_details": get_card_details,
}

SECURITY_OFFICER_TOOLS = {
    "update_card_transaction_limits": update_card_transaction_limits,
    "toggle_international_transactions": toggle_international_transactions,
}

FINANCIAL_ADVISOR_TOOLS = {
    "search_financial_playbook": search_financial_playbook,
}

# A dictionary mapping agent names to their specific toolsets.
AGENT_TOOLKITS = {
    "AccountSpecialist": ACCOUNT_SPECIALIST_TOOLS,
    "SecurityOfficer": SECURITY_OFFICER_TOOLS,
    "FinancialAdvisor": FINANCIAL_ADVISOR_TOOLS,
}

# Combine all tools into one dictionary for easy lookup by name.
ALL_TOOLS = {
    **ACCOUNT_SPECIALIST_TOOLS,
    **SECURITY_OFFICER_TOOLS,
    **FINANCIAL_ADVISOR_TOOLS,
}

# ==============================================================================
# === HELPER FUNCTIONS (Updated for new architecture) ==========================
# ==============================================================================

def get_tool_descriptions_for_agent(agent_name: str) -> str:
    """
    Inspects the tools for a specific agent and returns their
    descriptions in a structured format for the LLM.
    """
    tool_dict = AGENT_TOOLKITS.get(agent_name)
    if not tool_dict:
        return json.dumps([]) # Return empty list if agent has no tools

    tool_specs = []
    for func in tool_dict.values():
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

def get_tool_by_name(name: str):
    """Returns the actual tool function object from its name string."""
    return ALL_TOOLS.get(name)