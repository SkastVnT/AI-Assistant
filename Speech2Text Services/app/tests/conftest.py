"""
Pytest configuration for VistralS2T tests
Shared fixtures and settings
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_dir():
    """Get project root directory"""
    return project_root


@pytest.fixture(scope="session")
def app_dir():
    """Get app directory"""
    return project_root / "app"


@pytest.fixture(scope="session")
def output_dir(tmp_path_factory):
    """Create temporary output directory for tests"""
    return tmp_path_factory.mktemp("output")


@pytest.fixture
def sample_transcripts():
    """Sample transcripts for testing"""
    return {
        "whisper": "Xin chào tôi muốn hỏi về đơn hàng",
        "phowhisper": "Xin chào, tôi muốn hỏi về đơn hàng của tôi",
        "fused": "Khách hàng: Xin chào, tôi muốn hỏi về đơn hàng của tôi.",
    }


# Test markers
def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "gpu: marks tests requiring GPU (deselect with '-m \"not gpu\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
