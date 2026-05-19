# Brand assets

- **`aftertone-logo.png`** — horizontal lockup (icon + wordmark) for the README header.
- **`adapters/`** — README “Works with” icons (Cursor still uses Simple Icons CDN; Claude, Codex, OpenCode are vendored SVGs). Claude mark and OpenAI knot paths from [Simple Icons](https://simpleicons.org/) (MIT). OpenCode mark from [opencode.ai/brand](https://opencode.ai/brand) / [anomalyco/opencode](https://github.com/anomalyco/opencode) brand assets (not Simple Icons).

If the file is missing locally, copy the logo from your machine into this folder. Example (path from a Cursor-saved asset):

```bash
cp "$HOME/.cursor/projects/home-el-khal-omar-Desktop-supertonic/assets/logo-bf5e0ad7-8caf-46fa-8863-3fc046684d61.png" "$(git rev-parse --show-toplevel)/img/aftertone-logo.png"
```

Then `git add img/aftertone-logo.png` and commit.
