"""
ResearchPilot AI — LLM Factory
Returns Groq (with auto-detected available model or GROQ_MODEL) as primary,
with automatic fallback to alternative models / Gemini (GEMINI_MODEL).
Import get_llm() in any node.
"""
import os
from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage

load_dotenv()

_DETECTED_GROQ_MODEL = None


def _normalize_response(msg):
    """Ensure response.content is always a string, even if provider returns blocks/lists."""
    if hasattr(msg, "content"):
        content = msg.content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                else:
                    parts.append(str(item))
            return AIMessage(
                content="".join(parts),
                additional_kwargs=getattr(msg, "additional_kwargs", {})
            )
        elif not isinstance(content, str):
            return AIMessage(
                content=str(content),
                additional_kwargs=getattr(msg, "additional_kwargs", {})
            )
    return msg


def _resolve_groq_model(api_key: str) -> str:
    global _DETECTED_GROQ_MODEL
    if _DETECTED_GROQ_MODEL:
        return _DETECTED_GROQ_MODEL

    env_model = os.getenv("GROQ_MODEL")
    if env_model:
        _DETECTED_GROQ_MODEL = env_model.strip()
        return _DETECTED_GROQ_MODEL

    preferred_candidates = [
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
    ]

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        available_models = {m.id for m in client.models.list().data}
        for cand in preferred_candidates:
            if cand in available_models:
                _DETECTED_GROQ_MODEL = cand
                return cand
    except Exception:
        pass

    _DETECTED_GROQ_MODEL = "openai/gpt-oss-120b"
    return _DETECTED_GROQ_MODEL


def get_llm(temperature: float = 0.4, max_tokens: int = 4096):
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")

    if not groq_key and not gemini_key:
        raise ValueError(
            "No LLM API key found. Set GROQ_API_KEY or GOOGLE_API_KEY in .env"
        )

    groq_key = groq_key.strip() if groq_key else None
    gemini_key = gemini_key.strip() if gemini_key else None

    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip()

    models_to_chain = []

    if groq_key:
        from langchain_groq import ChatGroq
        primary_groq_model = _resolve_groq_model(groq_key)
        models_to_chain.append(
            ChatGroq(model=primary_groq_model, temperature=temperature, max_tokens=max_tokens, api_key=groq_key)
        )
        # Add backup Groq models if primary was not already one of them
        backup_groq_models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
        for b_mod in backup_groq_models:
            if b_mod != primary_groq_model:
                models_to_chain.append(
                    ChatGroq(model=b_mod, temperature=temperature, max_tokens=max_tokens, api_key=groq_key)
                )

    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        models_to_chain.append(
            ChatGoogleGenerativeAI(model=gemini_model, temperature=temperature, max_output_tokens=max_tokens, api_key=gemini_key)
        )

    primary = models_to_chain[0]
    fallbacks = models_to_chain[1:]

    if fallbacks:
        runnable = primary.with_fallbacks(fallbacks)
    else:
        runnable = primary

    return runnable | RunnableLambda(_normalize_response)

