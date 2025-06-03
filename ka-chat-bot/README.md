---
title: "Knowledge Assistant Chatbot"
language: python
author: "Taiga Matsumoto"
date: 2025-05-26
---

# Databricks Chatbot Application

Chat applications powered by your Databricks' Knowledge Assistant endpoint.

## Features

- 🚀 Real-time chat interface
- 💾 Chat history persistence
- 🔄 Message regeneration capability
- ⚡ Streaming responses
- 🔒 On-behalf-of-user authentication
- 🎯 Rate limiting and error handling

## Architecture

The application is built with:
- FastAPI for the backend API
- SQLite for chat history storage
- React frontend


## Getting Started

1. Clone the repository
2. Create an .env file with the following:
    - `LOCAL_API_TOKEN`: your PAT used only for local development
    - `DATABRICKS_HOST`: your Databricks domain url (e.g. "your-domain@databricks.com")
    - `SERVING_ENDPOINT_NAME`: your Knowledge Assistant's serving endpoint (e.g "ka-123-endpoint")

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Build the frontend

    [1]. Navigate to the frontend directory:

    ```bash
    cd frontend
    ```

    [2]. Install dependencies:

    ```bash
    npm install
    ```
    [3a]. Generate a local build:

    ```bash
    npm run build
    ```

    [3b]. Generate a production build for app deployment:

    ```bash
    npm run build:prod
    ```

5. Run the server:
    ```bash
    python main.py
    ```

## Key Components

- `fronted/`: React frontend
- `main.py`: FastAPI application entry point
- `utils/`: Helper functions and utilities
- `models.py`: Data models and schemas
- `chat_database.py`: Database interactions
