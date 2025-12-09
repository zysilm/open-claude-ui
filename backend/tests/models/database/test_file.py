"""Tests for File database model."""

import pytest
from datetime import datetime
from sqlalchemy import select

from app.models.database import File
from app.models.database.file import FileType


@pytest.mark.unit
class TestFileModel:
    """Test cases for the File model."""

    @pytest.mark.asyncio
    async def test_create_file(self, db_session, sample_project):
        """Test creating a new file record."""
        file = File(
            project_id=sample_project.id,
            filename="script.py",
            file_path="src/script.py",
            file_type=FileType.INPUT,
            size=2048,
            mime_type="text/x-python",
        )
        db_session.add(file)
        await db_session.commit()
        await db_session.refresh(file)

        assert file.id is not None
        assert len(file.id) == 36
        assert file.project_id == sample_project.id
        assert file.filename == "script.py"
        assert file.file_path == "src/script.py"
        assert file.file_type == FileType.INPUT
        assert file.size == 2048
        assert file.mime_type == "text/x-python"

    @pytest.mark.asyncio
    async def test_file_types(self, db_session, sample_project):
        """Test FileType enum values."""
        input_file = File(
            project_id=sample_project.id,
            filename="input.txt",
            file_path="input.txt",
            file_type=FileType.INPUT,
            size=100,
        )
        output_file = File(
            project_id=sample_project.id,
            filename="output.txt",
            file_path="output.txt",
            file_type=FileType.OUTPUT,
            size=200,
        )
        db_session.add_all([input_file, output_file])
        await db_session.commit()

        assert input_file.file_type == FileType.INPUT
        assert input_file.file_type.value == "input"
        assert output_file.file_type == FileType.OUTPUT
        assert output_file.file_type.value == "output"

    @pytest.mark.asyncio
    async def test_file_with_hash(self, db_session, sample_project):
        """Test file with SHA-256 hash for deduplication."""
        file = File(
            project_id=sample_project.id,
            filename="data.csv",
            file_path="data/data.csv",
            file_type=FileType.INPUT,
            size=10240,
            hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
        db_session.add(file)
        await db_session.commit()
        await db_session.refresh(file)

        assert file.hash is not None
        assert len(file.hash) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_file_without_mime_type(self, db_session, sample_project):
        """Test file without MIME type."""
        file = File(
            project_id=sample_project.id,
            filename="unknown_file",
            file_path="unknown_file",
            file_type=FileType.OUTPUT,
            size=500,
        )
        db_session.add(file)
        await db_session.commit()
        await db_session.refresh(file)

        assert file.mime_type is None

    @pytest.mark.asyncio
    async def test_file_timestamps(self, db_session, sample_project):
        """Test file upload timestamp."""
        file = File(
            project_id=sample_project.id,
            filename="test.txt",
            file_path="test.txt",
            file_type=FileType.INPUT,
            size=100,
        )
        db_session.add(file)
        await db_session.commit()
        await db_session.refresh(file)

        assert isinstance(file.uploaded_at, datetime)

    @pytest.mark.asyncio
    async def test_file_project_relationship(self, db_session, sample_project):
        """Test file relationship with project."""
        file = File(
            project_id=sample_project.id,
            filename="related.py",
            file_path="related.py",
            file_type=FileType.INPUT,
            size=1000,
        )
        db_session.add(file)
        await db_session.commit()
        await db_session.refresh(file)

        assert file.project.id == sample_project.id
        assert file.project.name == sample_project.name

    @pytest.mark.asyncio
    async def test_multiple_files_per_project(self, db_session, sample_project):
        """Test multiple files per project."""
        files = [
            File(
                project_id=sample_project.id,
                filename=f"file{i}.py",
                file_path=f"src/file{i}.py",
                file_type=FileType.INPUT,
                size=i * 100,
            )
            for i in range(5)
        ]
        db_session.add_all(files)
        await db_session.commit()

        query = select(File).where(File.project_id == sample_project.id)
        result = await db_session.execute(query)
        all_files = result.scalars().all()

        assert len(all_files) == 5

    @pytest.mark.asyncio
    async def test_various_mime_types(self, db_session, sample_project):
        """Test files with various MIME types."""
        mime_types = [
            ("image.png", "image/png"),
            ("document.pdf", "application/pdf"),
            ("data.json", "application/json"),
            ("styles.css", "text/css"),
            ("page.html", "text/html"),
        ]

        for filename, mime_type in mime_types:
            file = File(
                project_id=sample_project.id,
                filename=filename,
                file_path=filename,
                file_type=FileType.INPUT,
                size=1000,
                mime_type=mime_type,
            )
            db_session.add(file)

        await db_session.commit()

        query = select(File).where(File.project_id == sample_project.id)
        result = await db_session.execute(query)
        all_files = result.scalars().all()

        assert len(all_files) == 5
        stored_mimes = {f.mime_type for f in all_files}
        expected_mimes = {m[1] for m in mime_types}
        assert stored_mimes == expected_mimes

    @pytest.mark.asyncio
    async def test_delete_file(self, db_session, sample_file):
        """Test deleting a file."""
        file_id = sample_file.id
        await db_session.delete(sample_file)
        await db_session.commit()

        query = select(File).where(File.id == file_id)
        result = await db_session.execute(query)
        deleted = result.scalar_one_or_none()

        assert deleted is None

    @pytest.mark.asyncio
    async def test_file_type_enum_values(self):
        """Test FileType enum values."""
        assert FileType.INPUT.value == "input"
        assert FileType.OUTPUT.value == "output"
        assert len(FileType) == 2
