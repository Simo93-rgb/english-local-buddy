"""
History Manager – Progress tracking and conversation logging
==============================================================
Manages writing incremental session logs to disk and periodically
running an LLM-based analysis to update the persistent user report.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Assessor Prompt – guides the LLM to analyze the student's conversation
# ---------------------------------------------------------------------------
ASSESSOR_SYSTEM_PROMPT = """\
You are an expert English Language Teacher and Assessor.
Your task is to analyze an English conversation between a student and an assistant, and update the student's persistent English Proficiency Report.

Instructions:
1. Review the existing report (if any) and the new conversation log.
2. Update the report to accurately reflect:
   - The student's current conversational abilities and confidence.
   - Any new grammatical, vocabulary, or pronunciation errors observed in the session.
   - Any improvements or resolved errors (e.g. mistakes that are no longer made or were corrected).
   - Any old errors that recurred.
3. Keep the report structured, clear, and actionable in Markdown format. Use exactly these sections:
   - # User English Proficiency Report
   - ## Summary of Abilities
   - ## Identified Strengths
   - ## Grammatical & Vocabulary Errors
     - **Active Issues**:
     - **Resolved / Improved**:
   - ## Recommended Focus Areas
4. Do NOT output any preamble, markdown code fences, or chat preamble. Return ONLY the raw updated Markdown report.
"""

BLANK_REPORT_TEMPLATE = """\
# User English Proficiency Report

## Summary of Abilities
- No sessions recorded yet. Start conversing to populate your profile.

## Identified Strengths
- N/A

## Grammatical & Vocabulary Errors
- **Active Issues**:
- **Resolved / Improved**:

## Recommended Focus Areas
1. Start speaking and practicing daily.
"""


class HistoryManager:
    """
    Manages incremental conversation logging and progress report updates.
    """

    def __init__(self, history_dir: str | None = None) -> None:
        self.history_dir = Path(history_dir or settings.HISTORY_DIR)
        self.sessions_dir = self.history_dir / "sessions"
        
        # Ensure directories exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key="lm-studio"
        )
        
        # In-memory turn counter to trigger periodic report updates (e.g. every 10 turns)
        self._turn_counters: dict[str, int] = {}
        # Simple lock to prevent concurrent LLM updates for the same session
        self._update_locks: dict[str, asyncio.Lock] = {}

    def get_session_file_path(self, session_id: str) -> Path:
        """Get the file path for the session's log file."""
        return self.sessions_dir / f"chat_log_{session_id}.md"

    def get_report_file_path(self) -> Path:
        """Get the file path for the single persistent report."""
        return self.history_dir / "user_report.md"

    async def start_session(self, session_id: str) -> None:
        """Initialise the session log file with header metadata."""
        self._turn_counters[session_id] = 0
        self._update_locks[session_id] = asyncio.Lock()
        
        session_file = self.get_session_file_path(session_id)
        if not session_file.exists():
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header = f"# English Buddy Chat Session – {timestamp_str}\nSession ID: {session_id}\n\n"
            await asyncio.to_thread(session_file.write_text, header, encoding="utf-8")
            logger.info("Started session log file: %s", session_file)

    async def add_turn_incremental(self, session_id: str, role: str, text: str) -> None:
        """
        Append a single turn (user or assistant) to the session log file on disk.
        Triggers an update to the user progress report every 10 turns.
        """
        session_file = self.get_session_file_path(session_id)
        
        # Ensure session log is initialised
        if not session_file.exists():
            await self.start_session(session_id)
            
        role_label = "User" if role.lower() == "user" else "Partner"
        log_entry = f"- **{role_label}**: {text}\n"
        
        # Append immediately to avoid losing data in case of crashes
        def _append():
            with open(session_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        await asyncio.to_thread(_append)
        
        # Increment turn counter
        self._turn_counters[session_id] = self._turn_counters.get(session_id, 0) + 1
        current_turns = self._turn_counters[session_id]
        
        # Auto-update report every 10 turns (approx. 5 turns of back-and-forth)
        if current_turns > 0 and current_turns % 10 == 0:
            logger.info("Session %s reached %d turns, triggering periodic progress report update...", session_id, current_turns)
            asyncio.create_task(self.update_progress_report(session_id))

    async def update_progress_report(self, session_id: str) -> str | None:
        """
        Analyse the session history and update the persistent user_report.md.
        """
        # Ensure only one update runs at a time for this session
        lock = self._update_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            session_file = self.get_session_file_path(session_id)
            report_file = self.get_report_file_path()
            
            if not session_file.exists():
                logger.warning("Session file does not exist, skipping report update: %s", session_file)
                return None
                
            # Read session log and existing report
            chat_log = await asyncio.to_thread(session_file.read_text, encoding="utf-8")
            
            if report_file.exists():
                existing_report = await asyncio.to_thread(report_file.read_text, encoding="utf-8")
            else:
                existing_report = BLANK_REPORT_TEMPLATE
                
            logger.info("Running LLM analysis to update progress report for session %s...", session_id)
            
            messages = [
                {"role": "system", "content": ASSESSOR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Existing Report:\n---\n{existing_report}\n---\n\n"
                        f"New Chat Session Log:\n---\n{chat_log}\n---\n\n"
                        f"Update and output the revised Markdown report now:"
                    )
                }
            ]
            
            try:
                response = await self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0.3,
                )
                
                updated_report = response.choices[0].message.content
                if updated_report:
                    updated_report = updated_report.strip()
                    # Write updated report
                    await asyncio.to_thread(report_file.write_text, updated_report, encoding="utf-8")
                    logger.info("Progress report user_report.md updated successfully.")
                    return updated_report
                else:
                    logger.warning("LLM returned empty progress report.")
                    return None
            except Exception as e:
                logger.error("Failed to update progress report: %s", e, exc_info=True)
                return None

    def cleanup_session_state(self, session_id: str) -> None:
        """Clean up memory resources associated with the session."""
        self._turn_counters.pop(session_id, None)
        self._update_locks.pop(session_id, None)
