"""
LLM (Large Language Model) Module
===================================
Conversational English partner powered by a local LLM via
LM Studio's OpenAI-compatible API (http://localhost:1234/v1).
"""

from __future__ import annotations

import logging
from collections import deque

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt – instructs the LLM to be a concise English conversation partner
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
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


class LLMManager:
    """
    Manages conversation with a local LLM via LM Studio's
    OpenAI-compatible API.

    Parameters
    ----------
    base_url : str
        LM Studio server URL (default ``http://localhost:1234/v1``).
    model : str
        Model identifier as listed by LM Studio.
    max_context_turns : int
        Maximum number of recent user+assistant message pairs to keep
        in the rolling context window.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        max_context_turns: int = 5,
    ) -> None:
        self.model = model
        self.max_context_turns = max_context_turns
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key="lm-studio",  # LM Studio doesn't check API keys
        )
        # Rolling context: stores the last N (user, assistant) message dicts
        self._history: deque[dict] = deque(maxlen=max_context_turns * 2)

        logger.info(
            "LLMManager initialised (model=%s, base_url=%s, context=%d turns)",
            model,
            base_url,
            max_context_turns,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_response(self, user_text: str) -> str:
        """
        Send the user's text to the LLM and return the assistant's reply.

        The conversation history is maintained automatically so the bot
        remembers recent exchanges.

        Parameters
        ----------
        user_text : str
            What the user said (ASR transcription).

        Returns
        -------
        str
            The LLM's response text.
        """
        # Append the user message to history
        self._history.append({"role": "user", "content": user_text})

        # Build the full message list: system + rolling history
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
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
