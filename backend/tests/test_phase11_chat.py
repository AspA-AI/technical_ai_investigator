from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import app
from services.chat_service import ChatService


class FakeLLMClient:
    def __init__(self) -> None:
        self.prompt = ""

    def generate_text(
        self, prompt: str, max_tokens: int = 0, temperature: float = 0.0
    ) -> str:
        self.prompt = prompt
        return "Chat response: analyzed investigation state."


class FakeInvestigationResult:
    def __init__(self, state_json: str, upload_id: str | None = None) -> None:
        self.state_json = state_json
        self.upload_id = upload_id


class FakeQuery:
    def __init__(self, investigation: FakeInvestigationResult) -> None:
        self._investigation = investigation

    def filter(self, *args, **kwargs):
        return self

    def one_or_none(self):
        return self._investigation


class FakeDB:
    def __init__(self, investigation: FakeInvestigationResult, upload=None) -> None:
        self._investigation = investigation
        self._upload = upload

    def query(self, model):
        if model.__name__ == "UploadedFile":
            return FakeUploadQuery(self._upload)
        return FakeQuery(self._investigation)


class FakeUploadQuery:
    def __init__(self, upload) -> None:
        self._upload = upload

    def filter(self, *args, **kwargs):
        return self

    def one_or_none(self):
        return self._upload


def test_chat_service_returns_llm_answer() -> None:
    state = {
        "summary": "Test summary of investigation.",
        "root_causes": [{"cause": "bearing wear", "confidence": 82}],
        "recommendations": ["Inspect bearing assembly"],
    }
    fake_db = FakeDB(FakeInvestigationResult(json.dumps(state)))
    llm_client = FakeLLMClient()
    service = ChatService(fake_db, llm_client=llm_client)

    answer = service.answer(1, "What is the likely root cause?", history=None)

    assert answer == "Chat response: analyzed investigation state."
    assert "root cause" in llm_client.prompt.lower()
    assert "bearing wear" in llm_client.prompt


def test_chat_greeting_responds_naturally() -> None:
    state = {"summary": "Test summary."}
    fake_db = FakeDB(FakeInvestigationResult(json.dumps(state)))
    llm_client = FakeLLMClient()
    service = ChatService(fake_db, llm_client=llm_client)

    answer = service.answer(1, "hello", history=None)

    assert "Hello" in answer or "hello" in answer
    # Ensure LLM was not invoked for greeting
    assert llm_client.prompt == ""


def test_chat_off_topic_gentle_redirect() -> None:
    state = {"summary": "Test summary."}
    fake_db = FakeDB(FakeInvestigationResult(json.dumps(state)))
    llm_client = FakeLLMClient()
    service = ChatService(fake_db, llm_client=llm_client)

    answer = service.answer(1, "How is my family doing?", history=None)

    assert "engineering" in answer.lower()
    # Ensure LLM was not invoked for off-topic
    assert llm_client.prompt == ""


def test_chat_includes_uploaded_raw_in_prompt() -> None:
    state = {
        "summary": "Test summary with upload.",
    }
    upload_id = "upload_xyz"

    test_csv = "timestamp,temperature\n2024-01-01T00:00:00Z,42\n"
    upload = type(
        "Upload",
        (),
        {
            "upload_id": upload_id,
            "filename": "sensor.csv",
            "content_text": test_csv,
        },
    )()

    fake_db = FakeDB(
        FakeInvestigationResult(json.dumps(state), upload_id=upload_id),
        upload=upload,
    )
    llm_client = FakeLLMClient()
    service = ChatService(fake_db, llm_client=llm_client)

    _ = service.answer(1, "Show me the uploaded data sample", history=None)

    assert "timestamp,temperature" in llm_client.prompt


def test_chat_off_topic_returns_refusal() -> None:
    state = {"summary": "Test summary."}
    fake_db = FakeDB(FakeInvestigationResult(json.dumps(state)))
    llm_client = FakeLLMClient()
    service = ChatService(fake_db, llm_client=llm_client)

    answer = service.answer(1, "How is my family doing?", history=None)

    assert "engineering" in answer.lower()
    # ensure LLM was not invoked for off-topic
    assert llm_client.prompt == ""


def test_chat_route_returns_answer(monkeypatch) -> None:
    class FakeChatService:
        def __init__(self, db):
            self.db = db

        def answer(self, investigation_id: int, question: str, history=None) -> str:
            return "Live chat response."

    monkeypatch.setattr("api.routes.chat.ChatService", FakeChatService)

    client = TestClient(app)
    response = client.post(
        "/api/investigations/1/chat", json={"question": "What happened?"}
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Live chat response."
