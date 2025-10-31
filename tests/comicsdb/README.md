# Comics Database Tests

This directory contains comprehensive test coverage for the `comicsdb` Django application, which is the core of the Metron comic book database.

## Test Structure

The test suite is organized into several categories:

### API Tests
Tests for the REST API endpoints ensuring proper authentication, authorization, and data handling:
- [test_api_arc.py](test_api_arc.py) - Story arc API endpoints
- [test_api_character.py](test_api_character.py) - Character API endpoints
- [test_api_creator.py](test_api_creator.py) - Creator (writers, artists, etc.) API endpoints
- [test_api_credits.py](test_api_credits.py) - Credits API endpoints
- [test_api_imprint.py](test_api_imprint.py) - Publisher imprint API endpoints
- [test_api_issue.py](test_api_issue.py) - Comic issue API endpoints
- [test_api_publisher.py](test_api_publisher.py) - Publisher API endpoints
- [test_api_role.py](test_api_role.py) - Creator role API endpoints
- [test_api_series.py](test_api_series.py) - Comic series API endpoints
- [test_api_team.py](test_api_team.py) - Team API endpoints
- [test_api_universe.py](test_api_universe.py) - Universe API endpoints

### View Tests
Tests for the web interface views and templates:
- [test_arc_views.py](test_arc_views.py) - Story arc detail and list views
- [test_character_views.py](test_character_views.py) - Character detail and list views
- [test_creator_views.py](test_creator_views.py) - Creator detail and list views
- [test_home_view.py](test_home_view.py) - Homepage and dashboard views
- [test_imprint_views.py](test_imprint_views.py) - Imprint detail and list views
- [test_issue_views.py](test_issue_views.py) - Issue detail and list views
- [test_publisher_views.py](test_publisher_views.py) - Publisher detail and list views
- [test_series_views.py](test_series_views.py) - Series detail and list views
- [test_team_views.py](test_team_views.py) - Team detail and list views
- [test_universe_views.py](test_universe_views.py) - Universe detail and list views
- [test_week_views.py](test_week_views.py) - Weekly release views

### Model Tests
Tests for Django models, business logic, and database operations:
- [test_models.py](test_models.py) - Tests for all database models including:
  - Model creation and string representation
  - Model properties and methods
  - URL generation (`get_absolute_url()`)
  - Verbose name plurals
  - Relationships and counts

### Form Tests
- [test_issue_form.py](test_issue_form.py) - Issue form validation and handling

### Management Command Tests
- [test_management.py](test_management.py) - Django management commands

### History Tests
- [test_history.py](test_history.py) - Change tracking and history functionality

## Test Configuration

- [conftest.py](conftest.py) - Pytest fixtures and configuration shared across comicsdb tests

## Running Tests

Run all comicsdb tests:
```bash
pytest tests/comicsdb/
```

Run a specific test file:
```bash
pytest tests/comicsdb/test_models.py
```

Run a specific test:
```bash
pytest tests/comicsdb/test_models.py::test_publisher_creation
```

## Test Coverage

This test suite covers:
- **Models**: All core database models (Publisher, Series, Issue, Creator, Character, Team, Arc, Universe, Imprint, Role, etc.)
- **API Endpoints**: Full REST API including authentication, permissions, CRUD operations
- **Views**: Web interface views, templates, and URL routing
- **Forms**: Form validation and data handling
- **Management Commands**: Custom Django management commands
- **History Tracking**: Audit trail and change history
