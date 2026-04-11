# Repo Audit — MorphIQ Product
**Date:** 2026-04-11  
**Purpose:** Pre-sharing audit for employer review

---

## CRITICAL (must fix before sharing)

- **`.env` file exists in working directory** — contains a live `ANTHROPIC_API_KEY` value. It has never been committed to git (gitignored correctly), but it physically exists and would be visible when sharing the folder. Delete it: `rm .env`. Users should populate from `.env.example`.
- **`debug-c11422.log` at root level** — 56 KB Cursor IDE debug log. Not committed, but visible. Delete it: `rm debug-c11422.log`. (`.cursor/debug-c11422.log` also present — delete both.)

---

## RECOMMENDED (should fix)

- **`docs/internal/` folder is public** — Contains `PORTAL_BUILD_SPEC.md`, `PORTAL_CURSOR_GUIDE_v2.md`, `BULK_IMPORT_SPEC.md`, `COWORK_CONTEXT.md`. These are verbose internal specs and AI pairing session notes. The folder is named "internal" but is tracked in git and fully visible. Either remove before sharing or move outside the repo.
- **`portal_new/portal/` is likely abandoned legacy code** — This nested directory (`portal_new/portal/static/` and `portal_new/portal/templates/`) appears to be an old iteration. Active files are at `portal_new/static/` and `portal_new/templates/`. Confirm it's unused and delete.
- **`test_data/` contains 37 JPEG files (~5.8 MB total)** — Listed in `.gitignore` so not committed, but physically present. Clean up the working directory if sharing as a zip or giving direct folder access.
- **`TODO` in `portal_new/templates/overview.html:202`** — `<!-- TODO: wire to API -->`. Minor, but visible. Either wire it or remove the comment.

---

## CLEAN (no action needed)

- **No hardcoded API keys, passwords, or tokens** in any source file. `ANTHROPIC_API_KEY` appears only as `os.getenv("ANTHROPIC_API_KEY")` — correct.
- **`.gitignore` coverage is excellent** — covers `.env`, `portal.db`, `portal.db-journal`, `__pycache__/`, `*.pyc`, `*.log`, `debug-*.log`, `node_modules/`, `.DS_Store`, `Clients/`, `temp/`, `test_data/`, `test_doc_generator/`, `.claude/`, `.cursor/`.
- **`.env` was never committed** — `git log --all --full-history -- .env` returns nothing.
- **`portal.db` was never committed** — confirmed clean.
- **No `.key` or `.pem` files** ever committed.
- **No debug print statements** in Python source (`print("DEBUG"` / `print("TEST"` — zero matches).
- **No legacy `portal/` top-level directory** — only `portal_new/` exists.
- **`.bat` files are clean** — use relative paths and `%~dp0` only; no hardcoded personal directory paths.
- **Email addresses** appear only in documentation, seed scripts, and test data — no personal emails in source code.
- **No phone numbers** found in any source file.
- **Git history is professional** — commit messages are descriptive and technical. No personal info or financial references.
- **`README.md` is excellent** — professional tone, architecture diagram, tech stack table, screenshots, setup instructions, honest AI disclosure. No issues.
- **No `.log` files committed** — gitignored correctly.
- **`portal.db`** — present in working directory but gitignored and never committed.
- **Screenshot binaries** in `docs/screenshots/` (4 PNGs, ~1 MB total) — justified for documentation.
- **Logo assets** in `portal_new/static/` — justified.

---

## Git History (last 20 commits)

```
c859672 Security fixes, DB stability, multi-tenant onboarding — 2026-04-06
5b354fe Add product screenshots
854212e Add screenshots section with pipeline narrative
3eeb9e2 Remove personal data and internal docs before going public
f11a965 Restructure repo, fix compliance strip, client session, and add README
9a081b9 Full project state — March 2026
f4f0807 Connect portal frontend to real database
862f4e4 Fix UTF-8 encoding and .env API key loading
4ebb472 Add AI prefill pipeline and portal backend
```

**Assessment:** All commit messages are clean, technical, and professional. No flags.

---

## Summary

| Category | Status |
|---|---|
| Hardcoded secrets in source | CLEAN |
| `.env` in working directory | **CRITICAL — DELETE** |
| `.env` ever committed | CLEAN |
| `portal.db` ever committed | CLEAN |
| Debug log at root | **CRITICAL — DELETE** |
| `.gitignore` completeness | CLEAN |
| `.bat` files | CLEAN |
| Debug print statements | CLEAN |
| TODO/FIXME comments | 1 minor (see above) |
| Emails / phone numbers in source | CLEAN |
| Legacy directories | 1 nested legacy dir (see above) |
| Large binaries | CLEAN (screenshots justified) |
| README quality | EXCELLENT |
| Git history | CLEAN |
| `docs/internal/` exposure | RECOMMENDED — review before sharing |
