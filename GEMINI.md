# Project Overview

This project is a full-stack application consisting of a Django backend with Django REST Framework and a React frontend built with Vite. It features a chatbot powered by the Gemini API, integrated with various financial services functionalities.

## Key Technologies:
- **Backend:** Django, Django REST Framework (DRF), Python
- **Frontend:** React, Vite, TypeScript, npm
- **Database:** SQLite (db.sqlite3)
- **AI/Chatbot:** Google Gemini API, CrewAI, LiteLLM

## Architecture:
- The backend provides REST API endpoints for data retrieval and manipulation, including chatbot functionalities.
- The frontend consumes these APIs to display dynamic content and interact with the chatbot.
- Static files for the React frontend are served directly by Django from `static/react`.

# Building and Running

## Backend Setup (Django)

1.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Apply Database Migrations:**
    ```bash
    python manage.py makemigrations chatbot
    python manage.py migrate
    ```

3.  **Set up Gemini API Key:**
    Create a `.env` file in the project root (`IDFCFame5/`) and add your Gemini API key:
    ```
    GEMINI_API_KEY=YOUR_GEMINI_API_KEY
    ```
    Replace `YOUR_GEMINI_API_KEY` with your actual key obtained from Google AI Studio.

4.  **Populate Initial Data (Important!):**
    Many frontend components fetch data from the backend. For the application to function correctly, populate initial data for models like `InitialBotMessage`, `AIModel`, `SuggestedPrompt`, `ChatbotKnowledge`, `Notification`, `QuickStat`, `Account`, `Transaction`, `CreditCard`, `UserProfile`, `ChatMessage`, `UserNotificationSettings`, and `UserSecuritySettings`. You can do this via the Django Admin interface (accessible at `/admin/` after creating a superuser) or by creating a Django management command.

    To create a superuser:
    ```bash
    python manage.py createsuperuser
    ```

5.  **Run the Django development server:**
    ```bash
    python manage.py runserver
    ```
    The application will be available at `http://127.0.0.1:8000/`.
    The chat API endpoint is accessible at `http://127.0.0.1:8000/api/chat/`.

## Frontend Setup (React)

1.  **Navigate to the frontend directory:**
    ```bash
    cd react_frontend
    ```

2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```

3.  **Start the Vite development server:**
    ```bash
    npm run dev
    ```

4.  **Build the production-ready static files:**
    ```bash
    npm --prefix react_frontend run build
    ```
    The `vite.config.ts` is configured to output assets directly into the `static/react` directory with a `/static/` base path. Django serves these files directly.

# Development Conventions

## API Endpoints:
- All new API endpoints are **pluralized and lowercase** (e.g., `/api/userprofiles/`).
- **Authentication is not required** for the API endpoints.
- **Single Instance Models:** For models like `UserProfile`, `InitialBotMessage`, `UserNotificationSettings`, `UserSecuritySettings`, and `ChatbotKnowledge`, the API returns a list, and the frontend should access the first element (`data[0]`).

## Model Field Mapping:
- Frontend components are updated to correctly map to backend model field names (e.g., `account_type` instead of `type`, `card_number` instead of `number`).

## Logging:
- Logs are saved to `django.log` in the project's base directory.
- Internal server errors during chat processing display a generic message to the user; detailed errors are in `django.log`.

## Chatbot Specifics:
- The chatbot dynamically uses the Gemini model selected from the frontend, leveraging `crewai.llm.LLM`.
- The `model` parameter is passed with the `gemini/` prefix (e.g., `gemini/gemini-2.5-pro`).
- Supported Gemini models: `gemini-2.5-pro` (default), `gemini-2.5-flash`, `gemini-2.5-flash-lite`.
- Frontend correctly extracts raw string content from `CrewOutput` objects.

## Instructions Page:
- The "Instructions" page is handled by the React frontend. Content is fetched from `static/react/instructions.md`. To update, edit this Markdown file.
