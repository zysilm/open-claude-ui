"""Test script to manually trigger title generation for a specific chat session."""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import select
from app.core.storage.database import get_db
from app.models.database import ChatSession, Message, MessageRole, AgentConfiguration
from app.core.llm.provider import create_llm_provider_with_db


async def test_title_generation():
    """Test title generation for session 3ee36111-cf09-4c0e-8b7f-2323cbf3e453."""
    session_id = "3ee36111-cf09-4c0e-8b7f-2323cbf3e453"

    async for db in get_db():
        try:
            # Get session
            session_query = select(ChatSession).where(ChatSession.id == session_id)
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()

            if not session:
                print(f"❌ Session {session_id} not found")
                return

            print(f"📋 Session found:")
            print(f"   Name: {session.name}")
            print(f"   Title auto-generated: {session.title_auto_generated}")

            # Get first user message
            message_query = select(Message).where(
                Message.chat_session_id == session_id,
                Message.role == MessageRole.USER
            ).order_by(Message.created_at)
            message_result = await db.execute(message_query)
            messages = message_result.scalars().all()

            print(f"   User messages count: {len(messages)}")

            if len(messages) == 0:
                print("❌ No user messages found")
                return

            first_message = messages[0]
            print(f"   First message: {first_message.content[:100]}...")

            # Get agent config from session's project
            agent_config_query = select(AgentConfiguration).where(
                AgentConfiguration.project_id == session.project_id
            )
            agent_config_result = await db.execute(agent_config_query)
            agent_config = agent_config_result.scalar_one_or_none()

            if not agent_config:
                print("❌ No agent configuration found for this session's project")
                return

            print(f"\n🤖 Using agent configuration:")
            print(f"   Provider: {agent_config.llm_provider}")
            print(f"   Model: {agent_config.llm_model}")
            print(f"   Enabled tools: {agent_config.enabled_tools}")

            # Create LLM provider
            llm_provider = await create_llm_provider_with_db(
                provider=agent_config.llm_provider,
                model=agent_config.llm_model,
                llm_config=agent_config.llm_config,
                db=db,
            )

            print(f"   Has API key: {llm_provider._api_key is not None if hasattr(llm_provider, '_api_key') else 'Unknown'}")

            # Generate title
            prompt = f"""Generate a concise title (max 6 words) for a chat session based on this first user message:

"{first_message.content[:500]}"

Respond with ONLY the title, nothing else. The title should capture the main topic or intent."""

            print(f"\n🎯 Generating title...")
            title_response = ""
            async for chunk in llm_provider.chat([{"role": "user", "content": prompt}]):
                title_response += chunk
                print(f"   Chunk: {chunk}", end="", flush=True)
            print()  # New line

            # Clean up title
            generated_title = title_response.strip().strip('"').strip("'")[:100]

            print(f"\n✨ Generated title: '{generated_title}'")

            # Update session
            session.name = generated_title
            session.title_auto_generated = 'Y'
            await db.commit()

            print(f"✅ Session updated successfully!")

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

        break  # Exit after first iteration


if __name__ == "__main__":
    asyncio.run(test_title_generation())
