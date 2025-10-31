# User Management Tests

This directory contains tests for the `users` Django application, which handles user authentication, profiles, and account management.

## Test Files

### Model Tests
- [test_models.py](test_models.py) - Tests for the CustomUser model:
  - User creation and validation
  - Superuser creation with proper permissions
  - Required field validation (username, email)
  - User model string representation

### View Tests
- [test_views.py](test_views.py) - Tests for user-related views:
  - **Profile views**: User profile page and detail view
  - **Account management**: Profile update, password change views
  - **Registration**: User signup functionality
  - **Forms**: CustomUserChangeForm validation
  - **Templates**: Correct template rendering for all views
  - **URL routing**: URL patterns and redirects

## Test Configuration

- [conftest.py](conftest.py) - Pytest fixtures for user tests including:
  - User authentication fixtures
  - Test user creation
  - Login helpers

## Running Tests

Run all user tests:
```bash
pytest tests/users/
```

Run a specific test file:
```bash
pytest tests/users/test_models.py
```

Run a specific test:
```bash
pytest tests/users/test_models.py::test_user_creation
```

## Test Coverage

This test suite covers:
- **User Model**: Custom user model with email and username
- **Authentication**: Login, signup, and password management
- **Profile Management**: User profile views and updates
- **Forms**: User registration and profile update forms
- **Permissions**: Superuser creation and role validation
- **Views & Templates**: All user-facing pages and their templates
