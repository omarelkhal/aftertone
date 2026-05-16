---
name: aftertone-expression
description: Set Aftertone spoken-summary expression mode (Supertonic tags)
---

## Expression rule (required)

**Do not** plan or run shell first (unless the user gave a mode, e.g. `/aftertone-expression subtle`).

Your **first** tool call must be **AskQuestion** with options from:

```bash
AFTERTONE_ROOT="$(bash "${HOME}/.cursor/hooks/aftertone-root.sh" 2>/dev/null || echo "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
uv run --directory "${AFTERTONE_ROOT}/py" python speak_summary_config.py expression-picker
```

| id | meaning |
|----|---------|
| off | Plain speech; no expression tags |
| subtle | Sigh prefix when the agent sets `state="blocked"` on `<spoken_summary>` |
| expressive | Subtle plus breath on `state="debugging"` |
| passthrough | Keep one inline tag you write in the summary (advanced) |

## Apply

```bash
AFTERTONE_ROOT="$(bash "${HOME}/.cursor/hooks/aftertone-root.sh" 2>/dev/null || echo "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
uv run --directory "${AFTERTONE_ROOT}/py" python speak_summary_config.py set expression MODE
```

No daemon restart. Report stdout only.
