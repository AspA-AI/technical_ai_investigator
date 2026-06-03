"""OpenAI Embeddings client (Phase 4)."""

from openai import OpenAI

from config.settings import settings


class EmbeddingClient:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY or None)
        self._model = settings.OPENAI_EMBEDDING_MODEL

    def embed_text(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Cannot embed empty text")

        response = self._client.embeddings.create(
            model=self._model,
            input=cleaned,
        )
        return list(response.data[0].embedding)
