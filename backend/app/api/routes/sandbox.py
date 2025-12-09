"""Sandbox API routes for container management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.storage.database import get_db
from app.models.database import ChatSession, AgentConfiguration
from app.core.sandbox import get_container_manager, sanitize_command


router = APIRouter(prefix="/sandbox", tags=["sandbox"])


class ExecuteCommandRequest(BaseModel):
    """Request model for command execution."""

    command: str
    workdir: str = "/workspace"


class ExecuteCommandResponse(BaseModel):
    """Response model for command execution."""

    exit_code: int
    stdout: str
    stderr: str


class ContainerStatusResponse(BaseModel):
    """Response model for container status."""

    running: bool
    container_id: str | None
    stats: dict | None


@router.post("/{session_id}/start", status_code=status.HTTP_201_CREATED)
async def start_sandbox(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start a sandbox container for a chat session."""
    # Get chat session
    session_query = select(ChatSession).where(ChatSession.id == session_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )

    # Get agent configuration
    config_query = select(AgentConfiguration).where(
        AgentConfiguration.project_id == session.project_id
    )
    config_result = await db.execute(config_query)
    agent_config = config_result.scalar_one_or_none()

    if not agent_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent configuration not found",
        )

    # Create container
    manager = get_container_manager()
    try:
        container = await manager.create_container(
            session_id=session_id,
            env_type=agent_config.environment_type,
            environment_config=agent_config.environment_config,
        )

        # Update session with container ID
        session.container_id = container.container_id
        await db.commit()

        return {
            "message": "Sandbox started successfully",
            "container_id": container.container_id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sandbox: {str(e)}",
        )


@router.post("/{session_id}/stop")
async def stop_sandbox(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Stop sandbox container for a chat session."""
    manager = get_container_manager()

    try:
        success = await manager.destroy_container(session_id)

        if success:
            # Clear container ID from session
            session_query = select(ChatSession).where(ChatSession.id == session_id)
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()

            if session:
                session.container_id = None
                await db.commit()

            return {"message": "Sandbox stopped successfully"}
        else:
            return {"message": "Sandbox was not running"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop sandbox: {str(e)}",
        )


@router.post("/{session_id}/reset")
async def reset_sandbox(
    session_id: str,
):
    """Reset sandbox container to clean state."""
    manager = get_container_manager()

    try:
        success = await manager.reset_container(session_id)

        if success:
            return {"message": "Sandbox reset successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sandbox not found or not running",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset sandbox: {str(e)}",
        )


@router.get("/{session_id}/status", response_model=ContainerStatusResponse)
async def get_sandbox_status(
    session_id: str,
):
    """Get sandbox container status."""
    manager = get_container_manager()

    try:
        container = await manager.get_container(session_id)

        if container:
            stats = manager.get_container_stats(session_id)
            return ContainerStatusResponse(
                running=True,
                container_id=container.container_id,
                stats=stats,
            )
        else:
            return ContainerStatusResponse(
                running=False,
                container_id=None,
                stats=None,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sandbox status: {str(e)}",
        )


@router.post("/{session_id}/execute", response_model=ExecuteCommandResponse)
async def execute_command(
    session_id: str,
    request: ExecuteCommandRequest,
):
    """Execute a command in the sandbox."""
    manager = get_container_manager()

    try:
        container = await manager.get_container(session_id)

        if not container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sandbox not running. Start it first.",
            )

        # Sanitize command
        safe_command = sanitize_command(request.command)

        # Execute command
        exit_code, stdout, stderr = await container.execute(
            command=safe_command,
            workdir=request.workdir,
        )

        return ExecuteCommandResponse(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command execution failed: {str(e)}",
        )
