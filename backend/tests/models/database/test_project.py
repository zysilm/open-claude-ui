"""Tests for Project database model."""

import pytest
from datetime import datetime
from sqlalchemy import select

from app.models.database import Project


@pytest.mark.unit
class TestProjectModel:
    """Test cases for the Project model."""

    @pytest.mark.asyncio
    async def test_create_project(self, db_session):
        """Test creating a new project."""
        project = Project(
            name="Test Project",
            description="A test project description",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        assert project.id is not None
        assert len(project.id) == 36  # UUID format
        assert project.name == "Test Project"
        assert project.description == "A test project description"
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_project_without_description(self, db_session):
        """Test creating a project without description."""
        project = Project(name="Minimal Project")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        assert project.name == "Minimal Project"
        assert project.description is None

    @pytest.mark.asyncio
    async def test_project_id_auto_generation(self, db_session):
        """Test that project ID is auto-generated."""
        project = Project(name="Auto ID Project")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # ID should be a valid UUID string
        assert project.id is not None
        assert len(project.id) == 36
        assert project.id.count("-") == 4

    @pytest.mark.asyncio
    async def test_project_timestamps(self, db_session):
        """Test that timestamps are set correctly."""
        project = Project(name="Timestamp Test")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        assert project.created_at is not None
        assert project.updated_at is not None
        # created_at and updated_at should be very close for new records
        diff = abs((project.updated_at - project.created_at).total_seconds())
        assert diff < 1  # Less than 1 second difference

    @pytest.mark.asyncio
    async def test_project_query(self, db_session, sample_project):
        """Test querying a project."""
        query = select(Project).where(Project.id == sample_project.id)
        result = await db_session.execute(query)
        fetched = result.scalar_one()

        assert fetched.id == sample_project.id
        assert fetched.name == sample_project.name
        assert fetched.description == sample_project.description

    @pytest.mark.asyncio
    async def test_project_update(self, db_session, sample_project):
        """Test updating a project."""
        _original_updated_at = sample_project.updated_at

        sample_project.name = "Updated Project Name"
        sample_project.description = "Updated description"
        await db_session.commit()
        await db_session.refresh(sample_project)

        assert sample_project.name == "Updated Project Name"
        assert sample_project.description == "Updated description"

    @pytest.mark.asyncio
    async def test_project_delete(self, db_session, sample_project):
        """Test deleting a project."""
        project_id = sample_project.id
        await db_session.delete(sample_project)
        await db_session.commit()

        query = select(Project).where(Project.id == project_id)
        result = await db_session.execute(query)
        deleted = result.scalar_one_or_none()

        assert deleted is None

    @pytest.mark.asyncio
    async def test_multiple_projects(self, db_session):
        """Test creating multiple projects."""
        projects = [Project(name=f"Project {i}", description=f"Description {i}") for i in range(5)]
        db_session.add_all(projects)
        await db_session.commit()

        query = select(Project)
        result = await db_session.execute(query)
        all_projects = result.scalars().all()

        assert len(all_projects) == 5
        for i, project in enumerate(sorted(all_projects, key=lambda p: p.name)):
            assert project.name == f"Project {i}"
