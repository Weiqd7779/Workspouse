import sys
import os
import uuid
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path so we can import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server import app

def test_concurrency_state_isolation():
    """
    Test that variable state IS ISOLATED between two different clients 
    when the server uses session-based headers.
    """
    client = TestClient(app)
    
    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())

    headers_a = {"X-Session-ID": session_a}
    headers_b = {"X-Session-ID": session_b}

    # 1. User A sends a message
    msg_a = "Hello from User A"
    client.post("/chat", json={"message": msg_a}, headers=headers_a)

    # 2. User B sends a message
    msg_b = "Hello from User B"
    client.post("/chat", json={"message": msg_b}, headers=headers_b)

    # 3. Check User A's history
    resp_a = client.get("/history", headers=headers_a)
    history_a = resp_a.json()
    # Should contain msg_a
    assert any(m["content"] == msg_a for m in history_a), "User A should see their own message"
    # Should NOT contain msg_b
    assert not any(m["content"] == msg_b for m in history_a), "User A should NOT see User B's message"

    # 4. Check User B's history
    resp_b = client.get("/history", headers=headers_b)
    history_b = resp_b.json()
    # Should contain msg_b
    assert any(m["content"] == msg_b for m in history_b), "User B should see their own message"
    # Should NOT contain msg_a
    assert not any(m["content"] == msg_a for m in history_b), "User B should NOT see User A's message"

if __name__ == "__main__":
    # Manually run the test function if executed as script
    try:
        test_concurrency_state_isolation()
        print("Test PASSED: Sessions are isolated.")
    except AssertionError as e:
        print(f"Test FAILED: {e}")
    except Exception as e:
        print(f"Test CRASHED: {e}")
