---
name: aftertone-on
description: Turn Aftertone spoken TTS on for this chat only
---

## Agent rule

**No planning.** Run **only** the command below. Report stdout briefly. **No file edits.**

`cd` to the install root (first line of `~/.cursor/hooks/aftertone-install-dir`), then:

```
uv run --directory py python -m aftertone on
```

Enables spoken TTS **for this chat only**. This reply’s hook also **registers** this chat on the allowlist when you include the spoken line below.

## Required: `<spoken_summary>` on this reply

Default is **tag-only** (`summary_mode = tag_only` in `speak_summary.toml`): **no tag → silence**, even right after `/aftertone-on`.

After the CLI output, end **this** message with **`<spoken_summary>...</spoken_summary>`** (language = `lang` in `speak_summary.toml`; tone and punctuation per `.cursor/rules/spoken-summary.mdc`).

One short line is enough — e.g. spoken TTS is on for this chat; your next substantive replies can speak too.

Other chats stay silent until you run `/aftertone-on` in each one.
