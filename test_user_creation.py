"""Tests for user creation and input validation (app/users.py)

Covers:
- Password validation rules (minimum characters, maximum byte limits)
- User creation with default and custom roles
- Username regex and format validation
- Role constraints
- Duplicate user detection
"""

import pytest

from app import auth, models
from app.users import (
    MAX_PASSWORD_BYTES,
    MIN_PASSWORD_LENGTH,
    ROLES,
    UserError,
    create_user,
    validate_password,
)


# ---------------------------------------------------------------------------
# Password validation tests
# ---------------------------------------------------------------------------

def test_validate_password_valid():
    """Valid passwords meeting length and byte constraints pass validation."""
    validate_password("12345678")  # exactly 8 characters
    validate_password("a" * 72)     # exactly 72 ASCII bytes
    validate_password("A-secure_p@ssw0rd!123")


def test_validate_password_too_short():
    """Passwords shorter than MIN_PASSWORD_LENGTH raise UserError."""
    with pytest.raises(UserError, match=f"Password must be at least {MIN_PASSWORD_LENGTH} characters."):
        validate_password("short")

    with pytest.raises(UserError, match=f"Password must be at least {MIN_PASSWORD_LENGTH} characters."):
        validate_password("1234567")  # 7 characters


def test_validate_password_too_long_bytes():
    """Passwords exceeding MAX_PASSWORD_BYTES raise UserError."""
    # 73 ASCII characters = 73 bytes
    with pytest.raises(UserError, match=f"Password must be at most {MAX_PASSWORD_BYTES} bytes."):
        validate_password("a" * (MAX_PASSWORD_BYTES + 1))

    # Multi-byte UTF-8 characters: 25 * 3 bytes (euro sign is 3 bytes) = 75 bytes > 72 bytes
    with pytest.raises(UserError, match=f"Password must be at most {MAX_PASSWORD_BYTES} bytes."):
        validate_password("€" * 25)


# ---------------------------------------------------------------------------
# User creation tests
# ---------------------------------------------------------------------------

def test_create_user_success_default_role(client, db):
    """create_user successfully creates an employee by default with hashed password."""
    user = create_user(db, "valid_user", "password123")
    assert user.id is not None
    assert user.username == "valid_user"
    assert user.role == "employee"
    assert user.password_hash != "password123"
    assert auth.verify_password("password123", user.password_hash)

    # Persisted in database
    persisted = db.query(models.User).filter(models.User.username == "valid_user").first()
    assert persisted is not None
    assert persisted.id == user.id


def test_create_user_custom_role(client, db):
    """create_user allows specifying valid roles from ROLES."""
    for role in ROLES:
        user = create_user(db, f"user_{role}", "password123", role=role)
        assert user.role == role


@pytest.mark.parametrize(
    "valid_username",
    [
        "abc",                          # min length (3)
        "a" * 32,                       # max length (32)
        "user.name",                    # dot
        "user-name",                    # hyphen
        "user_name",                    # underscore
        "User123",                      # mixed alphanumeric
    ],
)
def test_create_user_valid_username_formats(client, db, valid_username):
    """Allowed characters (letters, digits, '.', '_', '-') within 3-32 chars succeed."""
    user = create_user(db, valid_username, "password123")
    assert user.username == valid_username


@pytest.mark.parametrize(
    "invalid_username",
    [
        "ab",                           # too short (<3 chars)
        "a" * 33,                       # too long (>32 chars)
        "user name",                    # contains space
        "user@domain",                  # contains @
        "user!",                        # contains !
        "user#1",                       # contains #
        "user$test",                    # contains $
        "",                             # empty string
    ],
)
def test_create_user_invalid_username(client, db, invalid_username):
    """Usernames not matching USERNAME_RE regex raise UserError."""
    with pytest.raises(UserError, match="Username must be 3-32 characters"):
        create_user(db, invalid_username, "password123")


def test_create_user_invalid_role(client, db):
    """Roles outside ROLES raise UserError."""
    with pytest.raises(UserError, match="Role must be one of:"):
        create_user(db, "valid_user", "password123", role="admin")

    with pytest.raises(UserError, match="Role must be one of:"):
        create_user(db, "valid_user", "password123", role="superuser")


def test_create_user_invalid_password(client, db):
    """Invalid passwords fail during user creation without persisting the user."""
    with pytest.raises(UserError):
        create_user(db, "valid_user", "short")

    assert db.query(models.User).filter(models.User.username == "valid_user").first() is None


def test_create_user_duplicate_username(client, db):
    """Creating a user with an already existing username raises UserError."""
    create_user(db, "duplicate_user", "password123")
    with pytest.raises(UserError, match="User 'duplicate_user' already exists."):
        create_user(db, "duplicate_user", "another_pass123")
