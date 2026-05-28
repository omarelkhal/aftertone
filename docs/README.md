# GitHub Pages (`/docs`)

Static site for [aftertone on GitHub Pages](https://omarelkhal.github.io/aftertone/).

- `index.html` — landing (includes `demo.mp4` walkthrough)
- `demo.mp4` — short + long task demo (~6 MB; served at `/demo.mp4` on Pages)
- `docs.html` — install, slash commands (Cursor + Claude + Codex), CLI, troubleshooting
- `adapters/claude.md` — Claude Code adapter (linked from docs; source on GitHub)
- `adapters/codex.md` — Codex adapter (global Stop hook + smoke test)

| File | URL |
|------|-----|
| `index.html` | Home — overview, flow, one-line install |
| `docs.html` | Documentation — install, **slash commands**, v2 CLI, Cursor, daemon, config, troubleshooting |
| `styles.css` | Shared styles |

**Publish:** Repository **Settings → Pages** → Source **Deploy from a branch** → Branch **`main`**, folder **`/docs`**.

**Preview locally:** open `index.html` or `docs.html` in a browser (relative links to `styles.css` work from the `docs/` folder).

**Note:** Logo uses the GitHub raw URL because `img/` lives at repo root, not under `docs/`.
