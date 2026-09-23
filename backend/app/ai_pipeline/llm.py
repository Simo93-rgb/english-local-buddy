from __future__ import annotations

import logging
from collections import deque
from pathlib import Path

from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback system prompt if markdown file cannot be read
DEFAULT_SYSTEM_PROMPT = """\
You are a friendly and encouraging English conversation partner.
Your goal is to help the user practise speaking English naturally.

Rules:
- Keep your responses very short: 1–2 sentences maximum.
- Use simple, clear English appropriate for a language learner.
- If the user makes a grammar or vocabulary mistake, gently correct it \
  in your reply without being condescending.
- Ask a follow-up question to keep the conversation flowing.
- Never switch to another language unless the user explicitly asks.
- Do not use markdown formatting or bullet points — speak naturally.
"""


def load_system_prompt(prompt_path: str | Path | None = None) -> str:
    """Load system prompt from a markdown file with fallback to default."""
    target_path = Path(prompt_path or settings.SYSTEM_PROMPT_PATH)
    if target_path.exists():
        try:
            content = target_path.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception as exc:
            logger.warning("Could not read prompt file %s: %s. Using default.", target_path, exc)
    return DEFAULT_SYSTEM_PROMPT.strip()


class LLMManager:
    """
    Manages conversation with a local LLM via OpenAI-compatible API
    (e.g., Unsloth Studio or LM Studio).

    Parameters
    ----------
    base_url : str | None
        LLM server URL (defaults to ``settings.LLM_BASE_URL``).
    model : str | None
        Model identifier (defaults to ``settings.LLM_MODEL``).
    api_key : str | None
        Bearer API token (defaults to ``settings.LLM_API_KEY``).
    prompt_path : str | Path | None
        Path to markdown system prompt (defaults to ``settings.SYSTEM_PROMPT_PATH``).
    max_context_turns : int
        Maximum number of recent user+assistant message pairs to keep
        in the rolling context window.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        prompt_path: str | Path | None = None,
        max_context_turns: int = 5,
    ) -> None:
        self.model = model or settings.LLM_MODEL
        self.base_url = base_url or settings.LLM_BASE_URL
        self.api_key = api_key or settings.LLM_API_KEY
        self.prompt_path = prompt_path or settings.SYSTEM_PROMPT_PATH
        self.max_context_turns = max_context_turns

        self._system_prompt = load_system_prompt(self.prompt_path)
        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )
        # Rolling context: stores the last N (user, assistant) message dicts per session
        self._histories: dict[str, deque[dict]] = {}
        self._default_history: deque[dict] = deque(maxlen=max_context_turns * 2)

        logger.info(
            "LLMManager initialised (model=%s, base_url=%s, prompt_path=%s, context=%d turns)",
            self.model,
            self.base_url,
            self.prompt_path,
            max_context_turns,
        )

    @property
    def _history(self) -> deque[dict]:
        """Backward-compatible access to the default history."""
        return self._default_history

    def get_history(self, session_id: str | None = None) -> deque[dict]:
        """Get or initialize history deque for a specific session."""
        if not session_id:
            return self._default_history
        if session_id not in self._histories:
            self._histories[session_id] = deque(maxlen=self.max_context_turns * 2)
        return self._histories[session_id]

    def reload_prompt(self) -> None:
        """Reload system prompt from disk."""
        self._system_prompt = load_system_prompt(self.prompt_path)
        logger.info("Reloaded system prompt from %s", self.prompt_path)

    def set_system_prompt(self, prompt: str) -> None:
        """Set an explicit system prompt string."""
        self._system_prompt = prompt.strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def _ensure_unsloth_model_loaded(self) -> None:
        """Attempt to auto-load the configured model via Unsloth Studio's API."""
        import httpx
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Enable auto-switch
                await client.put(
                    "http://127.0.0.1:8888/api/settings/openai-auto-switch",
                    headers=headers,
                    json={"enabled": True},
                )
                # Load requested model
                resp = await client.post(
                    "http://127.0.0.1:8888/v1/load",
                    headers=headers,
                    json={"model_path": self.model},
                )
                logger.info("Unsloth auto-load for '%s' returned status %d: %s", self.model, resp.status_code, resp.text[:100])
        except Exception as exc:
            logger.warning("Failed to auto-load model in Unsloth: %s", exc)

    async def get_response(
        self,
        user_text: str,
        system_prompt: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """
        Send the user's text to the LLM and return the assistant's reply.

        The conversation history is maintained automatically so the bot
        remembers recent exchanges in this session.

        Parameters
        ----------
        user_text : str
            What the user said (ASR transcription).
        system_prompt : str | None
            Optional per-request system prompt override.
        session_id : str | None
            Session identifier to maintain isolated conversation history.

        Returns
        -------
        str
            The LLM's response text.
        """
        import re

        history = self.get_history(session_id)

        # Append the user message to history
        history.append({"role": "user", "content": user_text})

        # Build the full message list: system + rolling history
        active_prompt = system_prompt or self._system_prompt
        messages = [
            {"role": "system", "content": active_prompt},
            *list(history),
        ]

        extra_body: dict[str, Any] = {}
        if not getattr(settings, "LLM_ENABLE_THINKING", False):
            extra_body["chat_template_kwargs"] = {"enable_thinking": False}

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1536,
                extra_body=extra_body if extra_body else None,
            )
        except Exception as exc:
            err_msg = str(exc).lower()
            if "no model loaded" in err_msg or "call post /inference/load" in err_msg:
                logger.info("Model not loaded in Unsloth. Auto-triggering model load and retrying...")
                await self._ensure_unsloth_model_loaded()
                try:
                    response = await self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1536,
                        extra_body=extra_body if extra_body else None,
                    )
                except Exception as retry_exc:
                    logger.error("LLM retry failed: %s", retry_exc)
                    if history and history[-1]["role"] == "user":
                        history.pop()
                    raise
            else:
                logger.error("LLM request failed: %s", exc)
                # Remove the user message we just added since we failed
                if history and history[-1]["role"] == "user":
                    history.pop()
                raise

        assistant_text = response.choices[0].message.content
        assistant_text = assistant_text.strip() if assistant_text else ""

        # Strip reasoning tags if model outputs them inside content (e.g. <think>...</think>)
        assistant_text = re.sub(r"<think>.*?</think>", "", assistant_text, flags=re.DOTALL).strip()

        # If content is empty (e.g. reasoning model ran long or put output in reasoning_content)
        if not assistant_text:
            reasoning = getattr(response.choices[0].message, "reasoning_content", None) or ""
            if reasoning and ("<it>" in reasoning or "<zh>" in reasoning):
                tag_matches = list(re.finditer(r"<(?:it|zh)>.*?</(?:it|zh)>", reasoning, re.DOTALL))
                if tag_matches:
                    start_pos = tag_matches[0].start()
                    end_pos = tag_matches[-1].end()
                    candidate = reasoning[start_pos:end_pos].strip()
                    if candidate:
                        logger.info("Recovered assistant response from reasoning_content (%d chars)", len(candidate))
                        assistant_text = candidate

        # Handle models that still output empty strings
        if not assistant_text:
            logger.warning("LLM returned an empty response. Falling back to default message.")
            assistant_text = "I'm sorry, I didn't quite catch that. Could you say it again?"
            if history and history[-1]["role"] == "user":
                history.pop()
        else:
            # Append valid assistant reply to history
            history.append({"role": "assistant", "content": assistant_text})

        logger.info("LLM response (session=%s): %s", session_id or "default", assistant_text[:80])
        return assistant_text

    def clear_history(self, session_id: str | None = None) -> None:
        """Reset the conversation context for a session or globally."""
        if session_id:
            if session_id in self._histories:
                self._histories[session_id].clear()
                logger.info("LLM conversation history cleared for session: %s", session_id)
        else:
            self._default_history.clear()
            self._histories.clear()
            logger.info("All LLM conversation histories cleared.")
