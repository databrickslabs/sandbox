# Feature Registry Tests

This directory contains unit tests for the Feature Registry Streamlit application.

## Setup

To install the required test dependencies:

```bash
pip install -r ../test-requirements.txt
```

## Running Tests

To run all tests:

```bash
python -m pytest
```

To run tests with coverage:

```bash
python -m pytest --cov=src
```

To run tests for a specific module:

```bash
python -m pytest tests/entities/test_features.py
```

## Test Structure

The tests are organized to mirror the structure of the main application:

- `entities/`: Tests for entity classes
  - `test_features.py`: Tests for feature-related classes
  - `test_tables.py`: Tests for table-related classes
  - `test_functions.py`: Tests for function-related classes

## Notes

These tests use mocks for the databricks-sdk components since they cannot be called directly from the test environment.