---
name: aftertone-off
description: Turn Aftertone spoken TTS off for this chat only
---

## Agent rule

**No planning.** Run **only** the command below. Report stdout briefly. **No file edits.**

`cd` to the install root (first line of `~/.cursor/hooks/aftertone-install-dir`), then:

```
uv run --directory py python -m aftertone off
```

Disables spoken TTS **for this chat only** (next hook removes it from the allowlist). Other chats are unchanged.

## Required: `<spoken_summary>` on this reply

With **tag-only** mode, end **this** message with **`<spoken_summary>...</spoken_summary>`** (same `lang` and rule as `.cursor/rules/spoken-summary.mdc`) — one short line that TTS is off for this chat.
