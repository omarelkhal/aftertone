## Summary

<!-- 1–3 bullets: what changed and why -->

## Test plan

- [ ] `bash scripts/bootstrap.sh` (if deps/assets touched)
- [ ] `bash py/test_speak_summary_pipeline.sh` (if hooks/daemon/audio touched)
- [ ] `bash py/diagnose_speak_hooks.sh` (if Cursor hook flow touched)

## Checklist

- [ ] I have read **[CONTRIBUTING.md](CONTRIBUTING.md)** and this PR matches project principles (privacy first, thin adapters).
- [ ] Docs updated if behavior or install changed.
