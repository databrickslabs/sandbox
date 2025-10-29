"""FastAPI application for Judge Builder."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.routers import router


def load_env_file(filepath: str) -> None:
    """Load environment variables from a file."""
    if Path(filepath).exists():
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    if key and value:
                        os.environ[key] = value


# Load .env files
load_env_file('.env')
load_env_file('.env.local')


def setup_logging() -> None:
    """Simple logging configuration."""
    debug_evaluation = os.getenv('DEBUG_EVALUATION', 'false').lower() == 'true'
    log_level = logging.DEBUG if debug_evaluation else logging.INFO

    logging.basicConfig(
        level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True
    )

    # Silence databricks.sdk INFO logs (e.g., "loading profile from ~/.databrickscfg")
    logging.getLogger('databricks.sdk').setLevel(logging.WARNING)

    # Silence urllib3 connection pool warnings
    logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)

    # Silence databricks.sdk INFO logs (e.g., "loading profile from ~/.databrickscfg")
    logging.getLogger('databricks.sdk').setLevel(logging.WARNING)

    print('Judge Builder - Server starting up')
    logging.debug('Judge Builder - Logging initialized')


# Setup logging
setup_logging()


# Monkey patch MLflow's call_chat_completions to use judge-builder client name
def _patch_mlflow_call_chat_completions():
    """Patch mlflow.genai.judges.utils.call_chat_completions to use judge-builder version."""
    try:
        import mlflow.genai.judges.utils as mlflow_utils
        from server.utils.constants import VERSION

        def patched_call_chat_completions(user_prompt: str, system_prompt: str, model: str | None = None, temperature: float | None = None):
            """Patched version that uses judge-builder client name."""
            from databricks.rag_eval import context, env_vars

            # Set our custom client name
            env_vars.RAG_EVAL_EVAL_SESSION_CLIENT_NAME.set(f"judge-builder-v{VERSION}")

            @context.eval_context
            def _call_chat_completions(user_prompt: str, system_prompt: str):
                managed_rag_client = context.get_context().build_managed_rag_client()
                kwargs = {
                    'user_prompt': user_prompt,
                    'system_prompt': system_prompt,
                }
                if model:
                    kwargs['model'] = model
                if temperature:
                    kwargs['temperature'] = temperature
                return managed_rag_client.get_chat_completions_result(**kwargs)

            return _call_chat_completions(user_prompt, system_prompt)

        # Apply the patch
        mlflow_utils.call_chat_completions = patched_call_chat_completions
        logging.info(f"Patched mlflow.genai.judges.utils.call_chat_completions to use judge-builder-v{VERSION}")
    except Exception as e:
        logging.warning(f"Failed to patch call_chat_completions: {e}")


# Apply patches on startup
_patch_mlflow_call_chat_completions()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    from server.services.judge_service import judge_service
    await judge_service.load_all_judges_on_startup()

    yield

    # Shutdown (if needed in the future)
    pass


app = FastAPI(
    title='Judge Builder API',
    description='API for LLM Judge Builder with MLflow integration',
    version='0.1.0',
    lifespan=lifespan,
    servers=[{'url': 'http://localhost:8001', 'description': 'Development server'}],
)

# Only enable CORS in development mode
if os.getenv('DEPLOYMENT_MODE', 'prod') == 'dev':
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

app.include_router(router, prefix='/api', tags=['api'])


@app.get('/health')
async def health():
    """Health check endpoint."""
    return {'status': 'healthy'}


# Serve static files from client build directory
if os.path.exists('client/build'):
    # First, mount static assets (CSS, JS, images, etc.)
    app.mount('/assets', StaticFiles(directory='client/build/assets'), name='assets')

    # Handle client-side routing - serve index.html for all non-API routes
    @app.get('/{full_path:path}')
    async def serve_spa(request: Request, full_path: str):
        """Serve the SPA for client-side routing."""
        # If it's an API route, let it pass through (this shouldn't happen due to mount order)
        if full_path.startswith('api/'):
            return None

        # Check if it's a request for a specific static file
        static_file_path = Path(f'client/build/{full_path}').resolve()
        build_dir = Path('client/build').resolve()

        # Prevent path traversal by ensuring the resolved path is within build_dir
        try:
            static_file_path.relative_to(build_dir)
            if static_file_path.exists() and static_file_path.is_file():
                return FileResponse(static_file_path)
        except ValueError:
            # Path is outside build_dir, serve index.html instead
            pass

        # For all other routes (client-side routes), serve index.html
        return FileResponse('client/build/index.html')
