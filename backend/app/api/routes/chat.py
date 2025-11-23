"""Chat session and message API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.core.storage.database import get_db
from app.models.database import ChatSession, Message, MessageRole, Project
from app.models.schemas import (
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatSessionListResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
)
from app.api.websocket import ChatWebSocketHandler

router = APIRouter(prefix="/chats", tags=["chat"])


# Chat Session endpoints
@router.get("", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    project_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List chat sessions, optionally filtered by project."""
    query = select(ChatSession)

    if project_id:
        query = query.where(ChatSession.project_id == project_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get chat sessions
    query = query.offset(skip).limit(limit).order_by(ChatSession.created_at.desc())
    result = await db.execute(query)
    sessions = result.scalars().all()

    return ChatSessionListResponse(
        chat_sessions=[ChatSessionResponse.model_validate(s) for s in sessions],
        total=total,
    )


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    project_id: str,
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    # Verify project exists
    project_query = select(Project).where(Project.id == project_id)
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )

    # Create chat session
    session = ChatSession(
        project_id=project_id,
        name=session_data.name,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ChatSessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a chat session by ID."""
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session with id {session_id} not found",
        )

    return ChatSessionResponse.model_validate(session)


@router.put("/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    session_data: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a chat session."""
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session with id {session_id} not found",
        )

    # Update fields
    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)

    await db.commit()
    await db.refresh(session)

    return ChatSessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session."""
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session with id {session_id} not found",
        )

    await db.delete(session)
    await db.commit()


# Message endpoints
@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    session_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List messages in a chat session."""
    # Verify session exists
    session_query = select(ChatSession).where(ChatSession.id == session_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session with id {session_id} not found",
        )

    # Get total count
    count_query = select(func.count()).select_from(Message).where(
        Message.chat_session_id == session_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get messages with agent actions
    query = (
        select(Message)
        .options(joinedload(Message.agent_actions))  # Eagerly load agent actions
        .where(Message.chat_session_id == session_id)
        .offset(skip)
        .limit(limit)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(query)
    messages = result.unique().scalars().all()

    return MessageListResponse(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=total,
    )


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    session_id: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new message in a chat session."""
    # Verify session exists
    session_query = select(ChatSession).where(ChatSession.id == session_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session with id {session_id} not found",
        )

    # Create message
    message = Message(
        chat_session_id=session_id,
        role=message_data.role or MessageRole.USER,
        content=message_data.content,
        message_metadata=message_data.message_metadata or {},
    )
    db.add(message)
    await db.commit()

    # Eagerly load agent_actions relationship to avoid lazy loading issues
    query = select(Message).options(joinedload(Message.agent_actions)).where(Message.id == message.id)
    result = await db.execute(query)
    refreshed_message = result.unique().scalar_one()

    return MessageResponse.model_validate(refreshed_message)


# WebSocket endpoint for streaming chat
@router.websocket("/{session_id}/stream")
async def chat_stream(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for streaming chat responses."""
    handler = ChatWebSocketHandler(websocket, db)
    await handler.handle_connection(session_id)
