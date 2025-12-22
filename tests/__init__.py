"""
Policy Validation Copilot Test Suite

This package contains comprehensive tests for the Policy Validation Copilot system:
- Unit tests for all modules and components
- Integration tests for workflows and services
- End-to-end tests covering all 14 use cases
- Performance tests for scalability validation
- Test fixtures and utilities for test data management
- Code coverage reporting and quality metrics
"""

import os
import sys
import pytest
from pathlib import Path

# Add src directory to Python path for testing
test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

# Test configuration
TEST_CONFIG = {
    "database_url": "sqlite:///test.db",
    "redis_url": "redis://localhost:6379/1",
    "use_mock_services": True,
    "log_level": "DEBUG",
    "test_timeout": 30,
    "coverage_threshold": 80
}

# Test markers for pytest
pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.ml_services", 
    "tests.fixtures.workflow",
    "tests.fixtures.test_data"
]

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for service interactions"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests for complete workflows"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 5 seconds"
    )
    config.addinivalue_line(
        "markers", "external: Tests requiring external services"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add slow marker to tests that might be slow
        if "performance" in item.nodeid or "e2e" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # Add external marker to tests requiring external services
        if "external" in item.nodeid or "integration" in item.nodeid:
            item.add_marker(pytest.mark.external)
