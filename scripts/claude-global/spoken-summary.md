# Spoken summary (Aftertone / Claude Code)

Aftertone is enabled when you run **`/aftertone_on`**. A **Stop** hook in `~/.claude/settings.json` speaks a short line via local TTS after each turn.

Use explicit text inside `<spoken_summary>...</spoken_summary>` in your **final** assistant message. With **`only_speak_spoken_summary = true`** (default), **only** the tag is spoken — no trimmed reply heuristics.

**`lang` in TOML = language of the spoken words.** The hook does **not** translate. Write the tag in the same language as **`lang`**.

**Quality depends on this tag** — treat it as a **flow briefing for someone listening, not looking at the screen**: hybrid pair-programmer voice (technical enough to trust, human enough to keep momentum). Not a changelog, not filler.

## What the listener needs (vibe coder)

Answer, in order of priority:

1. **State** — what happened: success, failure, discovery, decision, or blocker.
2. **Significance** — why it matters for the session (only when it changes what they should think).
3. **Steering** — the next move when it helps control the flow (not every reply).

**Next-step policy:** Include a next move for blockers, risk, tests due, open decisions, incomplete work, or an obvious action. Skip it for trivial acks or when the written reply already ends with a clear “your turn.”

**Tone:** Calm senior pair programmer — direct, warm, confident.

## When to include the tag

- Include for **substantive** answers (implementation, debugging, design, review, exploration, multi-sentence replies).
- **Skip** for trivial replies (single word, pure ack, “done”, emoji-only). With tag-only mode, silence is fine.

## Language (must match TOML `lang`)

<!-- autogen:spoken-lang:start -->
> **Locked `lang` for `<spoken_summary>` only:** `en` (from `~/aftertone/.cursor/hooks/speak_summary.toml` on global install). Write the **inner tag** only in that language — **not** the conversation language. After changing `lang`, run `/aftertone-lang` or `uv run --directory py python sync_spoken_rule_lang.py` from the Aftertone repo.
<!-- autogen:spoken-lang:end -->

- Read **`lang`** in `~/aftertone/.cursor/hooks/speak_summary.toml` (or your install’s `.cursor/hooks/speak_summary.toml`) before you write `<spoken_summary>`.
- Write **only** the inner tag text in the **natural language that matches that code**.
- The **rest** of your reply can stay in whatever language fits the user; the tag must follow **`lang`**.

## What goes inside the tag (only this is spoken)

- **One or two short sentences on purpose** (capped by **`spoken_summary_max_chars`**, default 360).
- **Plain language only:** no markdown, bullets, code, file paths, URLs, or hashes in the tag.
- **Lead with state, not process.**
- Put the block **at the very end** of the message:

```
<spoken_summary>
Your line here.
</spoken_summary>
```

Do **not** put `state="..."` on the opening tag. Do **not** use Supertonic inline expression tags in the body.

## Lively delivery (Supertonic prosody)

End **each sentence** inside `<spoken_summary>` with **one** of: `!!`, `??`, `?!`, or `!?` (vary them).

## Manual check when the user says “test”

If the user says **test** or asks to check speech, **always** end with `<spoken_summary>...</spoken_summary>` containing a short distinctive line in **`lang`**, with lively punctuation. Example: “Aftertone check: if you hear this, the hook and daemon are working!!”
