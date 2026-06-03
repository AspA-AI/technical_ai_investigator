"""Base protocol for deterministic investigation tools."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseTool(ABC, Generic[InputT, OutputT]):
    """Each tool lives in its own module; implement `run` in subclasses."""

    name: str = "base_tool"

    @abstractmethod
    def run(self, payload: InputT, **kwargs: Any) -> OutputT:
        raise NotImplementedError(f"{self.name} is not implemented yet.")
