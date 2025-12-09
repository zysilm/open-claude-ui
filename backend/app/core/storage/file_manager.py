"""File manager for workspace file operations."""

import os
import hashlib
import shutil
from pathlib import Path
from typing import List, BinaryIO
from datetime import datetime


class FileManager:
    """Manage files in project workspaces."""

    def __init__(self, base_path: str = "./data/project_files"):
        """
        Initialize file manager.

        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_project_path(self, project_id: str) -> Path:
        """Get path for project files."""
        project_path = self.base_path / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        return project_path

    def save_file(
        self,
        project_id: str,
        filename: str,
        content: BinaryIO,
    ) -> tuple[str, int, str]:
        """
        Save a file to project storage.

        Args:
            project_id: Project ID
            filename: Original filename
            content: File content stream

        Returns:
            Tuple of (file_path, size, hash)
        """
        project_path = self.get_project_path(project_id)

        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)

        # Handle duplicate filenames
        file_path = project_path / safe_filename
        if file_path.exists():
            base, ext = os.path.splitext(safe_filename)
            counter = 1
            while file_path.exists():
                safe_filename = f"{base}_{counter}{ext}"
                file_path = project_path / safe_filename
                counter += 1

        # Save file and calculate hash
        hasher = hashlib.sha256()
        size = 0

        with open(file_path, "wb") as f:
            while True:
                chunk = content.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
                f.write(chunk)
                size += len(chunk)

        file_hash = hasher.hexdigest()
        relative_path = str(file_path.relative_to(self.base_path))

        return relative_path, size, file_hash

    def get_file_path(self, relative_path: str) -> Path | None:
        """
        Get absolute path for a file.

        Args:
            relative_path: Relative path from base

        Returns:
            Absolute Path or None if doesn't exist
        """
        file_path = self.base_path / relative_path
        if file_path.exists() and file_path.is_file():
            return file_path
        return None

    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file.

        Args:
            relative_path: Relative path from base

        Returns:
            Success boolean
        """
        file_path = self.base_path / relative_path
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def list_project_files(self, project_id: str) -> List[dict]:
        """
        List all files in a project.

        Args:
            project_id: Project ID

        Returns:
            List of file info dicts
        """
        project_path = self.get_project_path(project_id)
        files = []

        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                relative_path = str(file_path.relative_to(self.base_path))

                files.append(
                    {
                        "path": relative_path,
                        "name": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        return files

    def delete_project_directory(self, project_id: str) -> bool:
        """
        Delete entire project directory and all its files.

        Call this when a project is deleted to clean up local files.

        Args:
            project_id: Project ID

        Returns:
            Success boolean
        """
        project_path = self.base_path / project_id
        try:
            if project_path.exists() and project_path.is_dir():
                shutil.rmtree(project_path)
                return True
            return True  # Already deleted or doesn't exist
        except Exception as e:
            print(f"Error deleting project directory {project_id}: {e}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal."""
        # Remove path separators
        filename = os.path.basename(filename)

        # Remove dangerous characters
        dangerous_chars = ["..", "/", "\\", "\0"]
        for char in dangerous_chars:
            filename = filename.replace(char, "_")

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext

        return filename


# Global file manager instance
_file_manager: FileManager | None = None


def get_file_manager() -> FileManager:
    """Get global file manager instance."""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager
