"""Tests for Project Pydantic schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.schemas.project import (
    ProjectBase,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)


@pytest.mark.unit
class TestProjectSchemas:
    """Test cases for Project schemas."""

    def test_project_base_valid(self):
        """Test valid ProjectBase schema."""
        project = ProjectBase(
            name="Test Project",
            description="A test project",
        )
        assert project.name == "Test Project"
        assert project.description == "A test project"

    def test_project_base_name_only(self):
        """Test ProjectBase with name only."""
        project = ProjectBase(name="Minimal Project")
        assert project.name == "Minimal Project"
        assert project.description is None

    def test_project_base_empty_name_fails(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectBase(name="")

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_short" for e in errors)

    def test_project_base_name_too_long(self):
        """Test that name exceeding max length fails."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectBase(name="x" * 256)

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_long" for e in errors)

    def test_project_create(self):
        """Test ProjectCreate schema."""
        project = ProjectCreate(
            name="New Project",
            description="Creating a new project",
        )
        assert project.name == "New Project"
        assert project.description == "Creating a new project"

    def test_project_update_partial(self):
        """Test ProjectUpdate with partial update."""
        update = ProjectUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.description is None

    def test_project_update_all_none(self):
        """Test ProjectUpdate with no fields."""
        update = ProjectUpdate()
        assert update.name is None
        assert update.description is None

    def test_project_update_description_only(self):
        """Test ProjectUpdate with description only."""
        update = ProjectUpdate(description="New description")
        assert update.name is None
        assert update.description == "New description"

    def test_project_response(self):
        """Test ProjectResponse schema."""
        now = datetime.utcnow()
        response = ProjectResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test Project",
            description="Test description",
            created_at=now,
            updated_at=now,
        )
        assert response.id == "123e4567-e89b-12d3-a456-426614174000"
        assert response.name == "Test Project"
        assert response.created_at == now
        assert response.updated_at == now

    def test_project_response_from_attributes(self):
        """Test ProjectResponse with from_attributes config."""

        # Simulate ORM model
        class MockProject:
            id = "test-id"
            name = "ORM Project"
            description = "From ORM"
            created_at = datetime.utcnow()
            updated_at = datetime.utcnow()

        response = ProjectResponse.model_validate(MockProject())
        assert response.id == "test-id"
        assert response.name == "ORM Project"

    def test_project_list_response(self):
        """Test ProjectListResponse schema."""
        now = datetime.utcnow()
        projects = [
            ProjectResponse(
                id=f"id-{i}",
                name=f"Project {i}",
                description=f"Description {i}",
                created_at=now,
                updated_at=now,
            )
            for i in range(3)
        ]
        response = ProjectListResponse(projects=projects, total=10)

        assert len(response.projects) == 3
        assert response.total == 10
        assert response.projects[0].name == "Project 0"

    def test_project_list_response_empty(self):
        """Test ProjectListResponse with empty list."""
        response = ProjectListResponse(projects=[], total=0)
        assert len(response.projects) == 0
        assert response.total == 0

    def test_project_name_min_length(self):
        """Test project name minimum length validation."""
        # Single character should be valid
        project = ProjectBase(name="A")
        assert project.name == "A"

    def test_project_name_max_length(self):
        """Test project name maximum length validation."""
        # 255 characters should be valid
        project = ProjectBase(name="x" * 255)
        assert len(project.name) == 255

    def test_project_description_long_text(self):
        """Test project with long description."""
        long_description = "Lorem ipsum " * 1000
        project = ProjectBase(name="Test", description=long_description)
        assert len(project.description) > 10000
