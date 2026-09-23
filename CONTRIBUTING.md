# Contributing to English Buddy

## Branching Policy
To maintain a clean and reliable history, please follow this strict branching policy:
- **`main`**: Production-ready code. Commits here should only come from merges.
- **`feat/<feature-name>`**: For new features. Commits must strictly adhere to the feature being developed.
- **`fix/<bug-name>`**: For bug fixes. Must solely contain code that addresses the specific bug.
- **`docs/<doc-update>`**: For documentation updates.

**Strict Adherence**: Do not mix features, bug fixes, or documentation updates in a single branch unless they are intrinsically linked. If a branch is named `fix/tts-language`, it must *only* contain changes to fix TTS language alignment.
