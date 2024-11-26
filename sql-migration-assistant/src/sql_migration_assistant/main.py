import os

from sql_migration_assistant.frontend.GradioFrontend import GradioFrontend


def main():
    frontend = GradioFrontend()
    frontend.app.queue().launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "localhost"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", 3001)),
    )


if __name__ == "__main__":
    main()
