# IDFCFame5

This is a Django project with a React frontend.

## Backend (Django)

The backend is a Django project. The main application is located in the `IDFC` directory.

### New Chatbot Functionality

A new Django app named `chatbot` has been added to handle AI chatbot functionalities. This includes:

*   **Chat API Endpoint**: A new endpoint `/api/chat/` has been introduced for text-based communication with the chatbot.
*   **Gemini Model Integration**: The chatbot now dynamically uses the Gemini model selected from the frontend, leveraging `crewai.llm.LLM` for integration. The `model` parameter is passed with the `gemini/` prefix (e.g., `gemini/gemini-2.5-pro`) to ensure `litellm` correctly identifies the provider. The supported models are `gemini-2.5-pro`, `gemini-2.5-flash`, and `gemini-2.5-flash-lite`.
*   **Voice Chat Integration (Future)**: Planned integration for accepting voice inputs and providing audio outputs.
*   **Settings Management (Future)**: Functionality to allow users to change chatbot settings.
*   **Financial Services Sales (Future)**: The chatbot will be able to offer relevant financial services.
*   **Financial Advice with Disclaimer (Future)**: The chatbot will provide financial advice based on a configurable playbook.

*   **Frontend Output Handling**: The frontend now correctly extracts the raw string content from the `CrewOutput` object received from the backend, preventing rendering errors and blank pages.

### New Data Models and API Endpoints

Several new data models and corresponding API endpoints have been introduced to support dynamic content fetching for the frontend.

*   `/api/userprofiles/`: Fetches user profile information (e.g., first name, mobile, customer ID). (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.) **Note: This model, along with `UserNotificationSettings` and `UserSecuritySettings`, is currently designed to hold global or default settings and is not directly linked to the Django `User` model via a foreign key. The frontend fetches the first available record.**
*   `/api/initialbotmessages/`: Retrieves the initial welcome message for the chatbot. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/aimodels/`: Lists available AI models for the chatbot. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/suggestedprompts/`: Provides a list of suggested prompts for the chatbot. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/chatbotknowledge/`: Manages the chatbot's knowledge base (GET and PUT). (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.) **Note: The `ChatbotKnowledgeSerializer` has been updated to make the `title` field read-only. This means that `PUT` requests to this endpoint should only contain the `knowledge_text` field.**
*   `/api/notifications/`: Fetches notifications. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/quickstats/`: Retrieves quick financial statistics. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/accounts/`: Lists bank accounts (not linked to a specific user for demo purposes), including their status and branch. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.) The `Account` model's string representation has been updated to reflect the removal of the `user` field, now displaying `account_type (account_number)`.
*   `/api/transactions/`: Provides a history of transactions. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/transactions/choices/`: Returns the available choices for `transaction_type`, `method`, and `category` fields.
*   `/api/creditcards/`: Fetches credit card details. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.) **Note: The `CreditCard` model now includes a `user` foreign key for user-specific credit card management.**
*   `/api/chatmessages/`: Stores and retrieves chat history. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/usernotificationsettings/`: Manages user notification preferences. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.) **Note: This model is currently designed to hold global or default settings and is not directly linked to the Django `User` model via a foreign key. The frontend fetches the first available record.**
*   `/api/usersecuritysettings/`: Manages user security settings. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.) **Note: This model is currently designed to hold global or default settings and is not directly linked to the Django `User` model via a foreign key. The frontend fetches the first available record.**
*   `/api/debitcardsettings/`: Manages debit card specific settings, including transaction limits and international usage. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/creditcardsettings/`: Manages credit card specific settings, including transaction limits and international usage. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)
*   `/api/instructions/`: Manages instructions. (Note: CSRF protection is explicitly exempted and authentication is disabled for this endpoint by setting `csrf_exempt = True` and `authentication_classes = []` in the viewset.)

### Logging Configuration

Logs are now saved to a file named `django.log` in the project's base directory. This file will store detailed log messages from both the `chatbot` application and the Django framework. The logging is configured with a rotating file handler, meaning it will automatically manage log file sizes and keep a certain number of backup files.

### Error Handling

Internal server errors encountered during chat processing will no longer display detailed error messages to the user in the frontend. Instead, a generic message "An internal error occurred while processing your request. Please try again later." will be displayed. Detailed error information will still be available in the `django.log` file.

### Running the Django Server

1.  **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Apply Database Migrations:**
    After pulling the latest changes, ensure your database is up-to-date by running:
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
    Many of the new frontend components now fetch data from the backend. For the application to function correctly, you will need to populate some initial data for models like `InitialBotMessage`, `AIModel`, `SuggestedPrompt`, `ChatbotKnowledge`, `Notification`, `QuickStat`, `Account`, `Transaction`, `CreditCard`, `UserProfile`, `ChatMessage`, `UserNotificationSettings`, `UserSecuritySettings`, `DebitCardSettings`, and `CreditCardSettings`. You can do this via the Django Admin interface (accessible at `/admin/` after creating a superuser) or by creating a Django management command.

    To create a superuser:
    ```bash
    python manage.py createsuperuser
    ```

5.  **Run the Django development server:**

    ```bash
    python manage.py runserver
    ```

    The application will be available at http://127.0.0.1:8000/.

    The new chat API endpoint is accessible at http://127.0.0.1:8000/api/chat/.

## Frontend (React)

The frontend is a React application built with Vite. The source files are located in the `react_frontend` directory.

### Frontend Data Fetching

The frontend components have been updated to fetch dynamic content from the new backend API endpoints. This includes:

*   **Chat Page**: Initial bot message, AI models, suggested prompts, and chat history.
*   **Dashboard Page**: User profile information (first name), notifications, and quick financial statistics.
*   **Account Overview Component**: User's bank account details.
*   **Transaction History Component**: Recent transaction records.
*   **Credit Card Section Component**: Credit card details.
*   **Transaction Management Page**: Fetches, adds, and deletes transaction records. Now fetches available `transaction_type`, `method`, and `category` options from the backend.
*   **Account Settings Page**: Fetches and updates personal information, notification preferences, security settings, account summaries, and now also **a single debit card setting (for the Savings Account) and credit card settings**.

### Frontend Development

To make changes to the frontend, you need to have Node.js and npm installed. Then, you can run the following commands in the `react_frontend` directory:

*   `npm install` to install the dependencies.
*   `npm run dev` to start the Vite development server.

    **Note:** After making changes to the frontend code, you will need to rebuild the frontend for the changes to take effect. Run `npm --prefix react_frontend run build` to rebuild the production-ready static files.

    **Note:** The `rehype-raw` and `react-syntax-highlighter` dependencies have been installed to resolve build issues.

**Note:** The chat interface now allows selection of specific Gemini models (`gemini-2.5-pro` (default), `gemini-2.5-flash`, `gemini-2.5-flash-lite`).

### Fix for TypeError: B.map is not a function

Resolved a `TypeError: B.map is not a function` occurring in the chat interface. This error was caused by the `aiModels` or `suggestedPrompts` data not being an array when fetched from the backend APIs (`/api/aimodels/` and `/api/suggestedprompts/`).

The fix involves adding `Array.isArray()` checks in `react_frontend/src/pages/Chat.tsx` before attempting to call `.map()` on the fetched data. This ensures that `aiModels` and `suggestedPrompts` are always treated as arrays, preventing the runtime error. If the API returns non-array data, the corresponding state is initialized with an empty array, and a console warning is logged.

### Building the Frontend

*   `npm --prefix react_frontend run build` to build the production-ready static files.
    The `vite.config.ts` has been updated to ensure `remark-gfm` is correctly bundled.

The Vite build process is configured (in `react_frontend/vite.config.ts`) to output assets directly into the `static/react` directory with a `/static/` base path. This means there is no need to manually copy files after building. Django is configured to serve these files directly from the `static/react` directory.

## Instructions Page

The "Instructions" page is now handled by the React frontend. When you navigate to `/instructions`, the React application loads, and the `Instructions` component fetches and renders the content from `static/react/instructions.md`. To update the content of this page, simply edit the `static/react/instructions.md` file.

## Troubleshooting

### Blank white page on loading

If you see a blank white page and console errors about MIME types or 404s for CSS/JS files, it's likely an issue with static file paths.

1.  **Django URL Configuration**: Ensure that your `IDFC/urls.py` is configured to serve static files during development. It should include:
    ```python
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # ... your other url patterns
    urlpatterns += staticfiles_urlpatterns()
    ```
2.  **Asset Paths in `index.html`**: Check that the asset paths in `static/react/index.html` are correct. They should be prefixed with `/static/`. For example:
    `<link rel="stylesheet" crossorigin href="/static/index-BSIXzmV2.css">
    If your frontend build process generates different paths, you may need to adjust them manually or configure the build process.

### 400 Bad Request Error on API Endpoints

If you encounter a `400 Bad Request` error when making POST or PUT requests to API endpoints (e.g., `/api/transactions/`), it indicates that the data being sent does not match the expected format or is missing required fields according to the Django REST Framework serializer.

To debug this:
1.  Open your browser's developer tools (usually by pressing F12).
2.  Go to the 'Network' tab.
3.  Make the API request that causes the 400 error.
4.  Click on the failed request (it will likely be red).
5.  Go to the 'Response' tab. This tab will display a JSON object with detailed error messages from the backend, indicating which fields are invalid or missing. For example:
    ```json
    {
        "field_name": [
            "This field is required."
        ],
        "another_field": [
            "\"invalid_value\" is not a valid choice."
        ]
    }
    ```
6.  **Additionally, check your Django server logs.** The `TransactionSerializer` has been modified to log detailed validation errors to the console when a `400 Bad Request` occurs. This will provide precise information about missing or invalid fields.
7.  Adjust the data sent from your frontend to match the serializer's requirements based on these error messages.