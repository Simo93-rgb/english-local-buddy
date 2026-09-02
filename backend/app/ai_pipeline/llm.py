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
        # Rolling context: stores the last N (user, assistant) message dicts
        self._history: deque[dict] = deque(maxlen=max_context_turns * 2)

        logger.info(
            "LLMManager initialised (model=%s, base_url=%s, prompt_path=%s, context=%d turns)",
            self.model,
            self.base_url,
            self.prompt_path,
            max_context_turns,
        )

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

    async def get_response(self, user_text: str, system_prompt: str | None = None) -> str:
        """
        Send the user's text to the LLM and return the assistant's reply.

        The conversation history is maintained automatically so the bot
        remembers recent exchanges.

        Parameters
        ----------
        user_text : str
            What the user said (ASR transcription).
        system_prompt : str | None
            Optional per-request system prompt override.

        Returns
        -------
        str
            The LLM's response text.
        """
        # Append the user message to history
        self._history.append({"role": "user", "content": user_text})

        # Build the full message list: system + rolling history
        active_prompt = system_prompt or self._system_prompt
        messages = [
            {"role": "system", "content": active_prompt},
            *list(self._history),
        ]

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )

            assistant_text = response.choices[0].message.content
            assistant_text = assistant_text.strip() if assistant_text else ""

            # Handle models that output empty strings (e.g. Gemma template mismatches)
            if not assistant_text:
                logger.warning("LLM returned an empty response. Falling back to default message.")
                assistant_text = "I'm sorry, I didn't quite catch that. Could you say it again?"
                # Do NOT append empty/fallback text to the history to avoid breaking the prompt template
                # We also remove the user's last message so they can just repeat it naturally
                if self._history and self._history[-1]["role"] == "user":
                    self._history.pop()
            else:
                # Append valid assistant reply to history
                self._history.append({"role": "assistant", "content": assistant_text})

            logger.info("LLM response: %s", assistant_text[:80])
            return assistant_text

        except Exception as exc:
            logger.error("LLM request failed: %s", exc)
            # Remove the user message we just added since we failed
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            raise

    def clear_history(self) -> None:
        """Reset the conversation context."""
        self._history.clear()
        logger.info("LLM conversation history cleared.")
