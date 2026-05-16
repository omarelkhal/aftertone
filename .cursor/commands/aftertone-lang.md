---
name: aftertone-lang
description: Set Aftertone spoken-summary language (lang in TOML + sync agent rule)
---

The user wants to change **`lang`** for spoken summaries. If they did not give a language code, ask once for a code (e.g. `en`, `fr`, `ja`). Supported codes are in `py/helper.py` `AVAILABLE_LANGS`.

Run **only** from the **repository root** (replace `CODE` with the chosen code):

```bash
uv run --directory py python speak_summary_config.py set lang CODE
```

Report command output. Remind them that `<spoken_summary>` text in replies should be written in that language. Do not edit `speak_summary.toml` manually.
