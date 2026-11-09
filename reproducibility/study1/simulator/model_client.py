"""Provider-neutral boundary between model calls and the paired experiment."""

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Protocol


@dataclass(frozen=True)
class Completion:
    """One transport result. Provider failures can carry billable token usage."""

    text: str | None
    status: str | None
    error: str | None
    input_tokens: int | None
    output_tokens: int | None
    audit: dict


class ModelClient(Protocol):
    def complete(self, request: str) -> str | Completion:
        """Return exact assistant text or a structured result for one stateless call."""


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def unique_object(fields: list[tuple]) -> dict:
    result = dict(fields)
    if len(result) != len(fields):
        raise ValueError("Duplicate JSON key")
    return result
