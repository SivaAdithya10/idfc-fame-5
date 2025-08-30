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

### Logging Configuration

Logs are now saved to a file named `django.log` in the project's base directory. This file will store detailed log messages from both the `chatbot` application and the Django framework. The logging is configured with a rotating file handler, meaning it will automatically manage log file sizes and keep a certain number of backup files.

### Error Handling

Internal server errors encountered during chat processing will no longer display detailed error messages to the user in the frontend. Instead, a generic message "An internal error occurred while processing your request. Please try again later." will be displayed. Detailed error information will still be available in the `django.log` file.

### Running the Django Server

1.  **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up Gemini API Key:**
    Create a `.env` file in the project root (`IDFCFame5/`) and add your Gemini API key:
    ```
    GEMINI_API_KEY=YOUR_GEMINI_API_KEY
    ```
    Replace `YOUR_GEMINI_API_KEY` with your actual key obtained from Google AI Studio.

3.  **Run the Django development server:**

    ```bash
    python manage.py runserver
    ```

    The application will be available at http://127.0.0.1:8000/.

    The new chat API endpoint is accessible at http://127.0.0.1:8000/api/chat/.

## Frontend (React)

The frontend is a React application built with Vite. The source files are located in the `react_frontend` directory.

### Frontend Development

To make changes to the frontend, you need to have Node.js and npm installed. Then, you can run the following commands in the `react_frontend` directory:

*   `npm install` to install the dependencies.
*   **Markdown Rendering Dependencies**: For the AI chatbot's messages to display in Markdown format, you need to install additional dependencies. Navigate to the `react_frontend` directory and run:
    ```bash
    npm install react-markdown rehype-raw remark-gfm react-syntax-highlighter
    ```
*   `npm run dev` to start the Vite development server.

    **Note:** After making changes to the frontend code, you will need to rebuild the frontend for the changes to take effect. Run `npm --prefix react_frontend run build` to rebuild the production-ready static files.

    **Note:** The `rehype-raw` and `react-syntax-highlighter` dependencies have been installed to resolve build issues.

**Note:** The chat interface now allows selection of specific Gemini models (`gemini-2.5-pro` (default), `gemini-2.5-flash`, `gemini-2.5-flash-lite`).

### Building the Frontend

*   `npm --prefix react_frontend run build` to build the production-ready static files.

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
    `<link rel="stylesheet" crossorigin href="/static/index-BSIXzmV2.css">`
    If your frontend build process generates different paths, you may need to adjust them manually or configure the build process.