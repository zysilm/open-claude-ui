"""Tests for sandbox security utilities."""

import pytest

from app.core.sandbox.security import (
    get_security_config,
    sanitize_command,
    validate_file_path,
    get_allowed_files_patterns,
    is_allowed_file,
)


@pytest.mark.unit
class TestGetSecurityConfig:
    """Test cases for get_security_config function."""

    def test_security_config_structure(self):
        """Test security config structure."""
        config = get_security_config()

        assert "privileged" in config
        assert "cap_drop" in config
        assert "cap_add" in config
        assert "security_opt" in config
        assert "mem_limit" in config
        assert "memswap_limit" in config
        assert "cpu_quota" in config

    def test_privileged_disabled(self):
        """Test that privileged mode is disabled."""
        config = get_security_config()
        assert config["privileged"] is False

    def test_capabilities_dropped(self):
        """Test that all capabilities are dropped."""
        config = get_security_config()
        assert config["cap_drop"] == ["ALL"]
        assert config["cap_add"] == []

    def test_security_options(self):
        """Test security options."""
        config = get_security_config()
        assert "no-new-privileges" in config["security_opt"]

    def test_resource_limits(self):
        """Test resource limit settings."""
        config = get_security_config()
        assert config["mem_limit"] == "1g"
        assert config["memswap_limit"] == "1g"
        assert config["cpu_quota"] == 50000  # 50% of one CPU


@pytest.mark.unit
class TestSanitizeCommand:
    """Test cases for sanitize_command function."""

    def test_safe_commands(self):
        """Test that safe commands pass through."""
        safe_commands = [
            "ls -la",
            "python script.py",
            "pip install requests",
            "cat file.txt",
            "echo 'Hello World'",
            "npm install",
            "node app.js",
            "pytest tests/",
        ]

        for cmd in safe_commands:
            result = sanitize_command(cmd)
            assert result == cmd

    def test_dangerous_rm_rf_patterns(self):
        """Test that dangerous rm -rf patterns are blocked.

        Note: The sanitize_command patterns are exact matches without spaces,
        e.g. ';rm -rf', '&&rm -rf', etc.
        """
        dangerous_commands = [
            "ls;rm -rf /",  # No space after semicolon
            "echo test;rm -rf /home",
            "cat file&&rm -rf /",  # No space after &&
            "ls|rm -rf /tmp",  # No space after |
            "$(rm -rf /)",
            "`rm -rf /`",
        ]

        for cmd in dangerous_commands:
            with pytest.raises(ValueError) as exc_info:
                sanitize_command(cmd)
            assert "dangerous command" in str(exc_info.value).lower()

    def test_case_insensitive_detection(self):
        """Test that dangerous patterns are detected case-insensitively."""
        dangerous_commands = [
            ";RM -RF /",
            ";Rm -Rf /home",
            "&&RM -rf /",
        ]

        for cmd in dangerous_commands:
            with pytest.raises(ValueError):
                sanitize_command(cmd)

    def test_rm_without_rf_allowed(self):
        """Test that rm without -rf is allowed."""
        # Note: The current implementation only blocks specific patterns
        # Regular rm commands should pass
        cmd = "rm file.txt"
        result = sanitize_command(cmd)
        assert result == cmd


@pytest.mark.unit
class TestValidateFilePath:
    """Test cases for validate_file_path function."""

    def test_valid_workspace_paths(self):
        """Test that valid workspace paths pass validation."""
        valid_paths = [
            "/workspace/out/script.py",
            "/workspace/project_files/data.csv",
            "/workspace/out/subdir/file.txt",
            "/workspace/test.py",
        ]

        for path in valid_paths:
            assert validate_file_path(path) is True

    def test_invalid_paths_outside_workspace(self):
        """Test that paths outside workspace are rejected."""
        invalid_paths = [
            "/etc/passwd",
            "/home/user/file.txt",
            "/tmp/script.py",
            "/var/log/system.log",
            "relative/path/file.txt",
        ]

        for path in invalid_paths:
            assert validate_file_path(path) is False

    def test_directory_traversal_blocked(self):
        """Test that directory traversal is blocked."""
        traversal_paths = [
            "/workspace/../etc/passwd",
            "/workspace/out/../../etc/passwd",
            "/workspace/out/../../../home/user",
        ]

        for path in traversal_paths:
            assert validate_file_path(path) is False

    def test_custom_allowed_base(self):
        """Test validation with custom allowed base."""
        assert validate_file_path("/custom/path/file.txt", allowed_base="/custom") is True
        assert validate_file_path("/other/path/file.txt", allowed_base="/custom") is False


@pytest.mark.unit
class TestGetAllowedFilesPatterns:
    """Test cases for get_allowed_files_patterns function."""

    def test_returns_patterns_list(self):
        """Test that function returns a list of patterns."""
        patterns = get_allowed_files_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) > 0

    def test_common_patterns_included(self):
        """Test that common file patterns are included."""
        patterns = get_allowed_files_patterns()

        expected = ["*.py", "*.js", "*.ts", "*.json", "*.md", "*.txt"]
        for pattern in expected:
            assert pattern in patterns

    def test_web_patterns_included(self):
        """Test that web file patterns are included."""
        patterns = get_allowed_files_patterns()

        web_patterns = ["*.html", "*.css"]
        for pattern in web_patterns:
            assert pattern in patterns


@pytest.mark.unit
class TestIsAllowedFile:
    """Test cases for is_allowed_file function."""

    def test_allowed_file_types(self):
        """Test that allowed file types return True."""
        allowed_files = [
            "script.py",
            "app.js",
            "component.ts",
            "component.tsx",
            "app.jsx",
            "config.json",
            "README.md",
            "data.txt",
            "data.csv",
            "config.yml",
            "config.yaml",
            "index.html",
            "styles.css",
            "query.sql",
            "script.sh",
            "script.bash",
        ]

        for filename in allowed_files:
            assert is_allowed_file(filename) is True, f"{filename} should be allowed"

    def test_disallowed_file_types(self):
        """Test that disallowed file types return False."""
        disallowed_files = [
            "program.exe",
            "library.dll",
            "archive.zip",
            "image.png",
            "document.pdf",
            "binary.bin",
            "script.php",
        ]

        for filename in disallowed_files:
            assert is_allowed_file(filename) is False, f"{filename} should be disallowed"

    def test_case_insensitive(self):
        """Test that file matching is case insensitive."""
        assert is_allowed_file("SCRIPT.PY") is True
        assert is_allowed_file("App.JS") is True
        assert is_allowed_file("README.MD") is True

    def test_no_extension(self):
        """Test files without extension."""
        assert is_allowed_file("Dockerfile") is False
        assert is_allowed_file("Makefile") is False
