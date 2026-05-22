---
name: aftertone-lang
description: Set Aftertone spoken-summary language (TOML + rule sync)
---

## Agent rule

**No planning.** Do not explain or run shell first unless the user gave a language code in this message (e.g. `/aftertone-lang fr`).

If no code was given, your **first** tool call must be **AskQuestion** (`allow_multiple: false`):

| id | label |
|----|-------|
| en | English (en) |
| fr | French (fr) |
| de | German (de) |
| es | Spanish (es) |
| it | Italian (it) |
| pt | Portuguese (pt) |
| ja | Japanese (ja) |
| ko | Korean (ko) |
| ar | Arabic (ar) |
| hi | Hindi (hi) |
| ru | Russian (ru) |
| nl | Dutch (nl) |
| pl | Polish (pl) |
| tr | Turkish (tr) |
| vi | Vietnamese (vi) |

If they need another code, ask once, then validate with `uv run --directory py python -m aftertone set lang CODE` (invalid codes error from the CLI).

## Apply (one command only)

`cd` to the install root (first line of `~/.cursor/hooks/aftertone-install-dir` or `%USERPROFILE%\.cursor\hooks\aftertone-install-dir`), then run **only**:

```
uv run --directory py python -m aftertone set lang CODE
```

Replace `CODE` with the pick or user value. No hand-editing TOML. No daemon restart. Report stdout only.

## After the command (same reply)

The CLI syncs **`lang`** into the spoken-summary rule. Tell the user the new code briefly.

**Required:** end **this** message with `<spoken_summary>...</spoken_summary>` written **only** in language **`CODE`** (the TOML language), even if the user has been chatting in another language. One short line that spoken TTS will use **`CODE`** from now on for the tag.
