# IDFCFame5

This is a Django project with a React frontend.

## Backend (Django)

The backend is a Django project. The main application is located in the `IDFC` directory.

### Running the Django Server

1.  **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Django development server:**

    ```bash
    python manage.py runserver
    ```

    The application will be available at http://127.0.0.1:8000/.

    A new endpoint `/transactions` has been added, accessible at http://127.0.0.1:8000/transactions.

## Frontend (React)

The frontend is a React application built with Vite. The source files are located in the `react_frontend` directory.

### Frontend Development

To make changes to the frontend, you need to have Node.js and npm installed. Then, you can run the following commands in the `react_frontend` directory:

*   `npm install` to install the dependencies.
*   `npm run dev` to start the Vite development server.

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