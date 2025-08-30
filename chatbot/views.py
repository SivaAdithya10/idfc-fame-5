# your_app/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from crewai import Agent, Task, Crew, Process
from django.conf import settings
# from crewai.llm import LLM # crewai_tools now handles this
from crewai.llm import LLM
import logging
import os

# Get an instance of a logger
logger = logging.getLogger(__name__)

class ChatView(APIView):
    def post(self, request, *args, **kwargs):
        user_message = request.data.get('message')
        # Get the conversation history from the request, default to an empty list
        history = request.data.get('history', []) 
        selected_model = request.data.get('model', 'gemini-2.5-flash-lite') # Default to a modern model

        if not user_message:
            logger.warning("ChatView received request with no message.")
            return Response({"error": "No message provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Configure Gemini LLM using environment variables for security
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
            logger.exception("Error configuring Gemini LLM.")
            return Response({"error": f"Failed to configure LLM"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Define a simple agent with an improved backstory for conversational context
        chatbot_agent = Agent(
            role='Customer Support Chatbot',
            goal='Continue the conversation with the user, providing helpful and concise answers based on the provided history and their latest message.',
            backstory='You are a helpful and friendly AI assistant for customer support, engaged in an ongoing conversation with a user. Your goal is to be natural and conversational.',
            verbose=True,
            allow_delegation=False,
            llm=llm,
            # memory=True # Enable memory for more complex, multi-step tasks within a single run.
                        # For simple request/response, passing history in the task is more direct.
        )

        # --- CONVERSATION HISTORY INTEGRATION ---
        # Format the history into a string for the agent's context
        formatted_history = ""
        if history:
            # We add a header to make it clear to the LLM what this section is
            formatted_history = "This is the conversation history so far:\n"
            for message in history:
                role = message.get('role', 'user') # Default to user if role is missing
                content = message.get('content', '')
                formatted_history += f"- {role.capitalize()}: {content}\n"
            formatted_history += "\n---\n"
        
        # Create a comprehensive task description including the history
        task_description = (
            f"{formatted_history}"
            f"Based on the conversation history above, provide a helpful and concise response to the user's latest message:\n"
            f"\"{user_message}\""
        )
        
        # Define a task for the agent using the new description
        chat_task = Task(
            description=task_description,
            agent=chatbot_agent,
            expected_output="A concise and helpful response that continues the conversation naturally."
        )

        try:
            logger.info(f"Attempting to kickoff CrewAI for user message: {user_message}")
            if history:
                logger.info(f"Conversation history contains {len(history)} messages.")

            crew = Crew(agents=[chatbot_agent], tasks=[chat_task], verbose=True) # This is the correct boolean value
            result = crew.kickoff()
            
            # The result from kickoff is the final string output
            bot_response = result.raw
            logger.info(f"CrewAI kickoff successful. Response: {bot_response[:100]}...")

        except Exception as e:
            logger.exception(f"Error during CrewAI kickoff for user message: {user_message}")
            error_message = f"Our engineers are fixing this. Kindly allow us sometime"
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"response": bot_response}, status=status.HTTP_200_OK)

