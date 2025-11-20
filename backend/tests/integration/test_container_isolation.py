"""Integration tests for container and file isolation between projects and sessions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.container
class TestContainerIsolation:
    """Test that containers and file access are properly isolated."""

    @pytest.mark.asyncio
    async def test_multiple_sessions_same_environment_get_separate_containers(
        self, skip_if_no_docker, db_session: AsyncSession
    ):
        """
        Test that multiple sessions using the same environment type (python3.11)
        get separate containers with isolated workspaces.
        """
        from app.core.sandbox.manager import get_container_manager
        from app.models.database import Project, ChatSession

        manager = get_container_manager()

        # Create two projects
        project1 = Project(name="Project 1", description="First project")
        project2 = Project(name="Project 2", description="Second project")
        db_session.add_all([project1, project2])
        await db_session.commit()
        await db_session.refresh(project1)
        await db_session.refresh(project2)

        # Create two sessions in different projects, both using python3.11
        session1 = ChatSession(project_id=project1.id, name="Session 1")
        session2 = ChatSession(project_id=project2.id, name="Session 2")
        db_session.add_all([session1, session2])
        await db_session.commit()
        await db_session.refresh(session1)
        await db_session.refresh(session2)

        container1 = None
        container2 = None

        try:
            # Create containers for both sessions using same environment type
            container1 = await manager.create_container(session1.id, "python3.11")
            container2 = await manager.create_container(session2.id, "python3.11")

            # Verify both containers exist and are running
            assert container1 is not None
            assert container2 is not None
            assert container1.is_running
            assert container2.is_running

            # Verify they are DIFFERENT containers
            assert container1.container.id != container2.container.id
            assert container1.container.name != container2.container.name

            # Verify container names include session IDs
            assert session1.id in container1.container.name
            assert session2.id in container2.container.name

            # Verify they have DIFFERENT workspaces
            assert container1.workspace_path != container2.workspace_path
            assert session1.id in container1.workspace_path
            assert session2.id in container2.workspace_path

        finally:
            # Cleanup
            if container1:
                await manager.destroy_container(session1.id)
            if container2:
                await manager.destroy_container(session2.id)

    @pytest.mark.asyncio
    async def test_file_isolation_between_sessions(
        self, skip_if_no_docker, db_session: AsyncSession
    ):
        """
        Test that files created in one session are NOT accessible from another session,
        even when both sessions are in the same project.
        """
        from app.core.sandbox.manager import get_container_manager
        from app.models.database import Project, ChatSession

        manager = get_container_manager()

        # Create one project
        project = Project(name="Shared Project", description="Project with multiple sessions")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # Create two sessions in the SAME project
        session1 = ChatSession(project_id=project.id, name="Session 1")
        session2 = ChatSession(project_id=project.id, name="Session 2")
        db_session.add_all([session1, session2])
        await db_session.commit()
        await db_session.refresh(session1)
        await db_session.refresh(session2)

        container1 = None
        container2 = None

        try:
            # Create containers for both sessions
            container1 = await manager.create_container(session1.id, "python3.11")
            container2 = await manager.create_container(session2.id, "python3.11")

            # Session 1: Create a file
            test_content_1 = "print('This is from session 1')"
            container1.write_file("/workspace/test_file.py", test_content_1)

            # Session 2: Create a file with same name but different content
            test_content_2 = "print('This is from session 2')"
            container2.write_file("/workspace/test_file.py", test_content_2)

            # Verify Session 1 still has its own content
            content_1 = container1.read_file("/workspace/test_file.py")
            assert content_1 == test_content_1
            assert "session 1" in content_1
            assert "session 2" not in content_1

            # Verify Session 2 has its own separate content
            content_2 = container2.read_file("/workspace/test_file.py")
            assert content_2 == test_content_2
            assert "session 2" in content_2
            assert "session 1" not in content_2

            # Verify the files are physically in different locations
            import os
            file1_path = os.path.join(container1.workspace_path, "test_file.py")
            file2_path = os.path.join(container2.workspace_path, "test_file.py")

            assert os.path.exists(file1_path)
            assert os.path.exists(file2_path)
            assert file1_path != file2_path  # Different physical paths

        finally:
            # Cleanup
            if container1:
                await manager.destroy_container(session1.id)
            if container2:
                await manager.destroy_container(session2.id)

    @pytest.mark.asyncio
    async def test_container_reuse_for_same_session(
        self, skip_if_no_docker, db_session: AsyncSession
    ):
        """
        Test that requesting a container for the same session multiple times
        returns the SAME container (reuse), not a new one.
        """
        from app.core.sandbox.manager import get_container_manager
        from app.models.database import Project, ChatSession

        manager = get_container_manager()

        # Create project and session
        project = Project(name="Test Project", description="Test")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        session = ChatSession(project_id=project.id, name="Test Session")
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        container = None

        try:
            # Create container first time
            container1 = await manager.create_container(session.id, "python3.11")
            container1_id = container1.container.id

            # Request container again for same session
            container2 = await manager.create_container(session.id, "python3.11")
            container2_id = container2.container.id

            # Should be the SAME container (reused)
            assert container1_id == container2_id
            assert container1.container.name == container2.container.name
            assert container1.workspace_path == container2.workspace_path

            # Verify only ONE container exists in Docker with this session name
            import docker
            client = docker.from_env()
            container_name = f"opencodex-sandbox-{session.id}"
            containers = client.containers.list(filters={"name": container_name})
            assert len(containers) == 1  # Only one container

            container = container1

        finally:
            # Cleanup
            if container:
                await manager.destroy_container(session.id)

    @pytest.mark.asyncio
    async def test_workspace_isolation_on_filesystem(
        self, skip_if_no_docker, db_session: AsyncSession
    ):
        """
        Test that session workspaces are physically isolated on the filesystem.
        """
        from app.core.sandbox.manager import get_container_manager
        from app.models.database import Project, ChatSession
        import os

        manager = get_container_manager()

        # Create project and two sessions
        project = Project(name="Test Project", description="Test")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        session1 = ChatSession(project_id=project.id, name="Session 1")
        session2 = ChatSession(project_id=project.id, name="Session 2")
        db_session.add_all([session1, session2])
        await db_session.commit()
        await db_session.refresh(session1)
        await db_session.refresh(session2)

        container1 = None
        container2 = None

        try:
            # Create containers
            container1 = await manager.create_container(session1.id, "python3.11")
            container2 = await manager.create_container(session2.id, "python3.11")

            # Verify workspace directories exist
            assert os.path.isdir(container1.workspace_path)
            assert os.path.isdir(container2.workspace_path)

            # Verify workspaces are in different directories
            assert container1.workspace_path != container2.workspace_path

            # Verify workspace paths contain session IDs
            assert session1.id in container1.workspace_path
            assert session2.id in container2.workspace_path

            # Verify standard subdirectories exist in each workspace
            for workspace in [container1.workspace_path, container2.workspace_path]:
                assert os.path.isdir(os.path.join(workspace, "project_files"))
                assert os.path.isdir(os.path.join(workspace, "agent_workspace"))
                assert os.path.isdir(os.path.join(workspace, "outputs"))

        finally:
            # Cleanup
            if container1:
                await manager.destroy_container(session1.id)
            if container2:
                await manager.destroy_container(session2.id)

    @pytest.mark.asyncio
    async def test_concurrent_file_operations_across_sessions(
        self, skip_if_no_docker, db_session: AsyncSession
    ):
        """
        Test that concurrent file operations in different sessions don't interfere.
        """
        from app.core.sandbox.manager import get_container_manager
        from app.models.database import Project, ChatSession
        import asyncio

        manager = get_container_manager()

        # Create project and sessions
        project = Project(name="Concurrent Test", description="Test")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        session1 = ChatSession(project_id=project.id, name="Session 1")
        session2 = ChatSession(project_id=project.id, name="Session 2")
        db_session.add_all([session1, session2])
        await db_session.commit()
        await db_session.refresh(session1)
        await db_session.refresh(session2)

        container1 = None
        container2 = None

        try:
            # Create containers
            container1 = await manager.create_container(session1.id, "python3.11")
            container2 = await manager.create_container(session2.id, "python3.11")

            # Define concurrent file operations
            async def write_multiple_files_session1():
                for i in range(5):
                    container1.write_file(
                        f"/workspace/file_{i}.txt",
                        f"Session 1 - File {i}"
                    )
                    await asyncio.sleep(0.01)

            async def write_multiple_files_session2():
                for i in range(5):
                    container2.write_file(
                        f"/workspace/file_{i}.txt",
                        f"Session 2 - File {i}"
                    )
                    await asyncio.sleep(0.01)

            # Run concurrent operations
            await asyncio.gather(
                write_multiple_files_session1(),
                write_multiple_files_session2()
            )

            # Verify each session has its own files with correct content
            for i in range(5):
                content1 = container1.read_file(f"/workspace/file_{i}.txt")
                content2 = container2.read_file(f"/workspace/file_{i}.txt")

                assert content1 == f"Session 1 - File {i}"
                assert content2 == f"Session 2 - File {i}"

                # No cross-contamination
                assert "Session 2" not in content1
                assert "Session 1" not in content2

        finally:
            # Cleanup
            if container1:
                await manager.destroy_container(session1.id)
            if container2:
                await manager.destroy_container(session2.id)
