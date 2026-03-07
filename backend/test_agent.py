from fastapi.testclient import TestClient
from app.main import app
import os
from dotenv import load_dotenv

load_dotenv()

client = TestClient(app)

def test_agent_query():
    # Make sure we have the key for the test
    assert os.getenv("GEMINI_API_KEY") is not None, "GEMINI_API_KEY is not set"
    
    response = client.post(
        "/agent/query",
        json={"query": "Why did the Red Sea shipping disruption happen?"},
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    assert "confidence" in data
    assert data["confidence"] in ["high", "medium", "low"]
    assert "query_type" in data
    print("Agent Query Response:", data)

def test_empty_query():
    response = client.post(
        "/agent/query",
        json={"query": ""},
    )
    assert response.status_code == 400

if __name__ == "__main__":
    test_agent_query()
    test_empty_query()
    print("All tests passed!")
