"""LLM helpers: Groq client plus robust JSON / text invocation."""
import os
import re
from typing import Type, TypeVar

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel

load_dotenv()

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "openai/gpt-oss-120b"


def get_llm(model: str | None = None, temperature: float = 0.2) -> ChatGroq:
    """Create a Groq chat model. Reads GROQ_API_KEY from the environment."""
    name = model or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    return ChatGroq(model=name, temperature=temperature, max_retries=4)


def _strip_think(text: str) -> str:
    """Qwen 3 may emit <think>...</think> reasoning; drop it."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def _strip_fences(text: str) -> str:
    m = re.match(r"^```[\w+.-]*\n(.*?)\n?```\s*$", text.strip(), flags=re.S)
    return m.group(1) if m else text


def _extract_json(text: str) -> str:
    text = _strip_fences(_strip_think(text))
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return text[start : end + 1]


def invoke_json(llm, system: str, user: str, schema: Type[T], retries: int = 3) -> T:
    """Ask the model for JSON matching `schema`; retry with error feedback.

    Parsing JSON ourselves (instead of relying on provider tool-calling) keeps
    this working across Kimi K2, Qwen 3 and any other Groq-hosted model.
    """
    import json

    schema_json = json.dumps(schema.model_json_schema())
    messages = [
        SystemMessage(
            content=f"{system}\n\nRespond with ONLY a valid JSON object that matches this "
            f"JSON schema. No prose, no markdown fences.\n{schema_json}"
        ),
        HumanMessage(content=user),
    ]
    last_error: Exception | None = None
    for _ in range(retries):
        raw = ""
        try:
            raw = llm.invoke(messages).content
            return schema.model_validate_json(_extract_json(raw))
        except ValueError as e:  # includes pydantic.ValidationError
            last_error = e
            messages.append(AIMessage(content=raw or "(empty)"))
            messages.append(
                HumanMessage(content=f"That output was invalid: {e}\nReturn corrected JSON only.")
            )
    raise RuntimeError(f"Model failed to return valid JSON after {retries} tries: {last_error}")


def invoke_text(llm, system: str, user: str) -> str:
    """Plain text/code completion with <think> and code fences removed."""
    out = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)]).content
    return _strip_fences(_strip_think(out)).rstrip() + "\n"
