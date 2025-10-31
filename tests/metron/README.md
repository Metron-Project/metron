# Metron Application Tests

This directory contains tests for the main `metron` Django application, which handles project-level functionality and configuration.

## Test Files

- [tests.py](tests.py) - Core application tests including:
  - API documentation view accessibility
  - 404 error handler
  - General application functionality

## Test Configuration

These tests verify that core project-level features work correctly, including:
- API documentation is accessible to authenticated users
- Custom error pages render properly
- Global application configuration

## Running Tests

Run all metron tests:
```bash
pytest tests/metron/
```

Run a specific test:
```bash
pytest tests/metron/tests.py::test_api_docs_url_exists_at_desired_location
```

## Coverage

This test suite ensures the main application layer functions correctly, including:
- Documentation accessibility
- Error handling
- Global middleware and configuration
