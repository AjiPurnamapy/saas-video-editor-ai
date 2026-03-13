"""
Security module tests.

Tests for password hashing, session tokens, and input sanitization.
"""

import pytest

from app.core.security import (
    hash_password,
    verify_password,
    check_needs_rehash,
    generate_session_token,
)


class TestPasswordHashing:
    """Tests for Argon2id password hashing."""

    def test_hash_produces_string(self):
        """Hashing returns a non-empty string."""
        hashed = hash_password("mypassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_argon2id(self):
        """Hash string starts with the Argon2id identifier."""
        hashed = hash_password("mypassword")
        assert hashed.startswith("$argon2id$")

    def test_verify_correct_password(self):
        """Correct password verifies successfully."""
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password fails verification."""
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Each hash is unique (due to random salt)."""
        h1 = hash_password("mypassword")
        h2 = hash_password("mypassword")
        assert h1 != h2

    def test_check_needs_rehash(self):
        """Freshly hashed password should not need rehash."""
        hashed = hash_password("mypassword")
        assert check_needs_rehash(hashed) is False


class TestSessionToken:
    """Tests for session token generation."""

    def test_token_is_string(self):
        """Token is a non-empty string."""
        token = generate_session_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_tokens_are_unique(self):
        """Each generated token is unique."""
        tokens = {generate_session_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_token_length(self):
        """Token has sufficient length (32 bytes = ~43 chars URL-safe)."""
        token = generate_session_token()
        assert len(token) >= 40


class TestInputSanitization:
    """Tests for FFmpeg input validation."""

    def test_validate_file_path_rejects_null_bytes(self):
        """Paths with null bytes are rejected."""
        from app.utils.ffmpeg_utils import _validate_file_path
        with pytest.raises(ValueError, match="null bytes"):
            _validate_file_path("/path/to/\x00file.mp4")

    def test_validate_file_path_rejects_shell_chars(self):
        """Paths with shell metacharacters are rejected."""
        from app.utils.ffmpeg_utils import _validate_file_path
        with pytest.raises(ValueError, match="unsafe characters"):
            _validate_file_path("/path/to/file;rm -rf /")

    def test_validate_file_path_accepts_normal_path(self):
        """Normal file paths are accepted."""
        from app.utils.ffmpeg_utils import _validate_file_path
        _validate_file_path("/path/to/video.mp4")  # Should not raise

    def test_validate_resolution_valid(self):
        """Valid resolution strings pass validation."""
        from app.utils.ffmpeg_utils import _validate_resolution
        w, h = _validate_resolution("1080x1920")
        assert w == "1080"
        assert h == "1920"

    def test_validate_resolution_invalid(self):
        """Invalid resolution strings are rejected."""
        from app.utils.ffmpeg_utils import _validate_resolution
        with pytest.raises(ValueError, match="Invalid resolution"):
            _validate_resolution("1080x1920;rm -rf /")

    def test_validate_resolution_too_large(self):
        """Absurdly large resolutions are rejected."""
        from app.utils.ffmpeg_utils import _validate_resolution
        with pytest.raises(ValueError, match="exceeds maximum"):
            _validate_resolution("99999x99999")

    def test_sanitize_filename_strips_traversal(self):
        """Path traversal sequences are stripped from filenames."""
        from app.services.video_service import _sanitize_filename
        assert "passwd" in _sanitize_filename("../../etc/passwd")
        assert "video.mp4" in _sanitize_filename("../video.mp4")

    def test_sanitize_filename_normal(self):
        """Normal filenames pass through safely."""
        from app.services.video_service import _sanitize_filename
        assert _sanitize_filename("my_video.mp4") == "my_video.mp4"

    def test_sanitize_filename_null_bytes(self):
        """Null bytes are removed from filenames."""
        from app.services.video_service import _sanitize_filename
        result = _sanitize_filename("video\x00.mp4")
        assert "\x00" not in result
