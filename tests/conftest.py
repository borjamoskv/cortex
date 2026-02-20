import pytest
import os
from cortex import api_state, config

@pytest.fixture(autouse=True)
def reset_cortex_state():
    """Reset global state and config between every test."""
    # 1. Reset api_state
    api_state.engine = None
    api_state.auth_manager = None
    api_state.tracker = None
    
    # 2. Reset config from environment
    config.reload()
    
    yield
    
    # 3. Cleanup after test
    api_state.engine = None
    api_state.auth_manager = None
    api_state.tracker = None
    config.reload()
