from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_chat_notification_email(
    user_input_query,
    main_agent_response,
    sub_agent_used,
    tools_used,
    sub_agent_response,
    final_output,
    chat_history
):
    subject = "Chatbot Interaction Notification"
    message = f"""
    A new chatbot interaction has occurred.

    User Input Query: {user_input_query}

    Main Agent Response: {main_agent_response}

    Sub Agent Used: {sub_agent_used if sub_agent_used else 'N/A'}

    Tools Used: {tools_used if tools_used else 'N/A'}

    Sub Agent Response: {sub_agent_response if sub_agent_response else 'N/A'}

    Final Output: {final_output}

    Chat History:
    {chat_history}
    """
    from_email = settings.EMAIL_HOST_USER
    recipient_list = settings.RECIPIENT_EMAIL

    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        logger.info("Chatbot interaction notification email sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send chatbot interaction notification email: {e}")
