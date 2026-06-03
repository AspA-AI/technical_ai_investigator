"""OpenAI LLM wrapper for phase 8 GPT integration."""

from __future__ import annotations
import json
from typing import Any

from openai import OpenAI

from config.settings import settings


class LLMClient:
    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()

        raise ValueError("OpenAI response contains no choices or content")
