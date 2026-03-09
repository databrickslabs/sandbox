"""
REST API endpoints for supervisor generation.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import List
import io
import zipfile

from app.db_adapter import WarehouseDB  # Auto-switches between SQLite and Warehouse
from app.schemas.supervisor import (
    SupervisorGenerateRequest,
    SupervisorGenerateResponse,
    SupervisorPreviewResponse,
    SupervisorMetadata,
    SupervisorListResponse,
)
from app.services.generator import GeneratorService, GeneratorError, get_generator_service
from app.services.audit import record_audit

router = APIRouter(prefix="/supervisors", tags=["Supervisors"])


@router.post(
    "/generate",
    response_model=SupervisorGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Supervisor",
    description="Generate a supervisor from a collection",
)
def generate_supervisor(
    request: SupervisorGenerateRequest,
    http_request: Request,
    generator: GeneratorService = Depends(get_generator_service),
) -> SupervisorGenerateResponse:
    """
    Generate a supervisor from a collection.

    Creates three files:
    - supervisor.py: Main supervisor code with Pattern 3
    - requirements.txt: Python dependencies
    - app.yaml: Databricks Apps deployment config

    The generated supervisor uses dynamic tool discovery at runtime.
    """
    try:
        # Generate supervisor code
        files = generator.generate_and_validate(
            collection_id=request.collection_id,
            llm_endpoint=request.llm_endpoint,
            app_name=request.app_name,
        )

        # Fetch collection for metadata
        collection = WarehouseDB.get_collection(request.collection_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection with id {request.collection_id} not found",
            )

        # Determine app name
        app_name = request.app_name
        if not app_name:
            # Normalize collection name to valid app name
            collection_name = collection.get('name', 'supervisor')
            app_name = collection_name.lower().replace(" ", "-")
            app_name = "".join(c for c in app_name if c.isalnum() or c == "-")

        # Persist supervisor metadata
        WarehouseDB.create_supervisor(
            collection_id=request.collection_id,
            app_name=app_name,
        )

        record_audit(http_request, "generate", "supervisor", resource_name=app_name,
                      details={"collection_id": request.collection_id})

        return SupervisorGenerateResponse(
            collection_id=collection.get('id'),
            collection_name=collection.get('name', ''),
            app_name=app_name,
            files=files,
            generated_at=datetime.utcnow().isoformat() + "Z",
            supervisor_url=f"/apps/{app_name}",
            code=files.get("supervisor.py"),
        )

    except GeneratorError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get(
    "/{collection_id}/preview",
    response_model=SupervisorPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview Supervisor",
    description="Preview generated files without full generation",
)
def preview_supervisor(
    collection_id: int,
    llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
    app_name: str = None,
    generator: GeneratorService = Depends(get_generator_service),
) -> SupervisorPreviewResponse:
    """
    Preview generated files before download.

    Returns metadata about what will be generated and a preview
    of each file (first 500 characters).
    """
    try:
        # Fetch collection
        collection = WarehouseDB.get_collection(collection_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection with id {collection_id} not found",
            )

        # Fetch collection items
        _, items = generator.fetch_collection_items(collection_id)

        # Resolve MCP server URLs
        mcp_server_urls = generator.resolve_mcp_server_urls(items)

        # Generate files
        files = generator.generate_supervisor_code(
            collection_id=collection_id,
            llm_endpoint=llm_endpoint,
            app_name=app_name,
        )

        # Determine app name
        if not app_name:
            collection_name = collection.get('name', 'supervisor')
            app_name = collection_name.lower().replace(" ", "-")
            app_name = "".join(c for c in app_name if c.isalnum() or c == "-")

        # Create preview (first 500 chars of each file)
        preview = {
            filename: content[:500] + ("..." if len(content) > 500 else "")
            for filename, content in files.items()
        }

        return SupervisorPreviewResponse(
            collection_id=collection.get('id'),
            collection_name=collection.get('name', ''),
            app_name=app_name,
            mcp_server_urls=mcp_server_urls,
            tool_count=len(items),
            preview=preview,
        )

    except GeneratorError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post(
    "/{collection_id}/download",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Download Supervisor",
    description="Download generated supervisor as zip archive",
)
def download_supervisor(
    collection_id: int,
    llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
    app_name: str = None,
    generator: GeneratorService = Depends(get_generator_service),
) -> StreamingResponse:
    """
    Download generated supervisor as a zip archive.

    The zip contains:
    - supervisor.py
    - requirements.txt
    - app.yaml

    Can be deployed directly to Databricks Apps.
    """
    try:
        # Fetch collection
        collection = WarehouseDB.get_collection(collection_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection with id {collection_id} not found",
            )

        # Generate files
        files = generator.generate_and_validate(
            collection_id=collection_id,
            llm_endpoint=llm_endpoint,
            app_name=app_name,
        )

        # Determine app name for filename
        if not app_name:
            collection_name = collection.get('name', 'supervisor')
            app_name = collection_name.lower().replace(" ", "-")
            app_name = "".join(c for c in app_name if c.isalnum() or c == "-")

        # Persist supervisor metadata
        WarehouseDB.create_supervisor(
            collection_id=collection_id,
            app_name=app_name,
        )

        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files.items():
                zip_file.writestr(filename, content)

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={app_name}.zip"
            },
        )

    except GeneratorError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get(
    "",
    response_model=SupervisorListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Supervisors",
    description="List generated supervisors with metadata",
)
def list_supervisors() -> SupervisorListResponse:
    """
    List all generated supervisors with metadata tracking.
    """
    supervisors, total = WarehouseDB.list_supervisors()
    return SupervisorListResponse(
        supervisors=[SupervisorMetadata(**s) for s in supervisors],
        total=total,
    )


@router.delete(
    "/{supervisor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Supervisor Metadata",
    description="Delete supervisor metadata (does not undeploy the app)",
)
def delete_supervisor(supervisor_id: int, request: Request) -> None:
    """
    Delete supervisor metadata.
    """
    deleted = WarehouseDB.delete_supervisor(supervisor_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supervisor with id {supervisor_id} not found",
        )
    record_audit(request, "delete", "supervisor", str(supervisor_id))
