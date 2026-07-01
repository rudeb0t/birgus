import uuid
import pytest


@pytest.fixture
def fake_uuid() -> uuid.UUID:
    return uuid.UUID("12345678-1234-5678-1234-567812345678")
