from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from crewai import Agent, Task, Crew, Process
from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

class ChatView(APIView):
    def post(self, request, *args, **kwargs):
        user_message = request.data.get('message')
        selected_model = request.data.get('model', 'gemini-2.5-pro') # Default to gemini-2.5-pro
        if not user_message:
            logger.warning("ChatView received request with no message.")
            return Response({"error": "No message provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Configure Gemini LLM
        gemini_api_key = settings.GEMINI_API_KEY
        if not gemini_api_key:
            logger.error("GEMINI_API_KEY is not set in settings.")
            return Response({"error": "Gemini API key not configured."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            llm = ChatGoogleGenerativeAI(
                model=selected_model,
                google_api_key=gemini_api_key
            )
        except Exception as e:
            logger.exception(f"Error configuring Gemini LLM: {e}")
            return Response({"error": "Failed to configure LLM."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Define a simple agent
        chatbot_agent = Agent(
            role='Customer Support Chatbot',
            goal='Provide helpful and concise answers to customer queries',
            backstory='You are an AI assistant for customer support.',
            verbose=True,
            allow_delegation=False,
            llm=llm
        )

        # Define a task for the agent
        chat_task = Task(
            description=f"Respond to the user's message: {user_message}",
            agent=chatbot_agent,
            expected_output="A concise and helpful response to the user's query."
        )

        # Create a Crew and kick it off
        crew = Crew(
            agents=[chatbot_agent],
            tasks=[chat_task],
            verbose=True, # Set to True for verbose output
            process=Process.sequential  # Tasks will be executed one after the other
        )

        try:
            logger.info(f"Attempting to kickoff CrewAI for user message: {user_message}")
            result = crew.kickoff()
            bot_response = result
            logger.info(f"CrewAI kickoff successful. Response: {bot_response[:100]}...") # Log first 100 chars
        except Exception as e:
            logger.exception(f"Error during CrewAI kickoff for user message: {user_message}")
            bot_response = f"An internal error occurred while processing your request. Please try again later. Error: {str(e)}"
            return Response({"error": bot_response}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"response": bot_response}, status=status.HTTP_200_OK)