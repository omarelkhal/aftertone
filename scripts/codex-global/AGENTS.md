## Aftertone spoken summaries for Codex

Aftertone speaks after a Codex turn when the global Codex `Stop` hook is installed and the current session is enabled.

Use explicit text inside `<spoken_summary>...</spoken_summary>` in your final assistant message. With `only_speak_spoken_summary = true` and `summary_mode = "tag_only"` by default, only the tag is spoken.

**`lang` in TOML = language of the spoken words.** The hook does not translate. Write the tag in the same language as `lang`, not necessarily the language the user typed.

<!-- autogen:spoken-lang:start -->
> **Locked `lang` for `<spoken_summary>` only:** `en` (from `~/aftertone/.cursor/hooks/speak_summary.toml` on global install). Write the **inner tag** only in that language — **not** the conversation language. After changing `lang`, run `/aftertone-lang` or `uv run --directory py python sync_spoken_rule_lang.py` from the Aftertone repo.
<!-- autogen:spoken-lang:end -->

Treat the tag as a short pair-programmer briefing for someone listening, not looking at the screen:

- State what happened.
- Add why it matters only when it changes the user's next thought.
- Add a next move only for blockers, risk, tests due, open decisions, incomplete work, or an obvious action.

Put exactly one block at the very end of substantive replies:

```xml
<spoken_summary>
The current session is ready to speak after Codex replies!!
</spoken_summary>
```

Do not put markdown, code, file paths, URLs, hashes, or `state="..."` in the spoken tag.

For livelier Supertonic delivery, end each sentence inside the tag with one of `!!`, `??`, `?!`, or `!?`.

If the user says `test` or asks to check speech, end with a short distinctive `<spoken_summary>` line in the configured language.
