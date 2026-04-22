# MorphIQ Deployment Checklist

This checklist is the safest order for pushing or deploying the Gemini-first MorphIQ portal.

## Required Environment Variables

- `GEMINI_API_KEY`
- `PORTAL_SECRET_KEY`

## Optional Environment Variables

- `GEMINI_MODEL_CHAT`
- `GEMINI_MODEL_DETECTION`
- `GEMINI_MODEL_EXTRACTION`
- `SENTRY_DSN`
- `FLASK_DEBUG`
- `CHAT_MAX_MESSAGE_CHARS`
- `CHAT_MAX_RESPONSE_CHARS`

## Local Pre-Push Checklist

1. Copy `.env.example` to `.env` if needed.
2. Set a real `GEMINI_API_KEY`.
3. Set a long random `PORTAL_SECRET_KEY`.
4. Run:

```powershell
& 'C:\morph-iq-portal\venv\Scripts\python.exe' -m unittest tests.test_ai_runtime tests.test_compliance_engine tests.test_portal_security_helpers -v
& 'C:\morph-iq-portal\venv\Scripts\python.exe' -m py_compile portal_new\ai_runtime.py portal_new\app.py ai_prefill.py auto_ocr_watch.py
& 'C:\morph-iq-portal\venv\Scripts\python.exe' scripts\scan_tracked_secrets.py
```

5. Review `git diff` before staging.
6. Confirm no real secrets, client exports, logs, or internal-only notes are staged.

## Local Smoke Checklist

1. Start the portal from the project root:

```powershell
& 'C:\morph-iq-portal\venv\Scripts\python.exe' portal_new\app.py
```

2. Verify login works with a valid seeded account.
3. Verify `/ask-ai` loads.
4. Verify `/api/chat` returns a Gemini-backed response.
5. Verify one manager-scoped portfolio view such as `/api/properties`.
6. Verify one CSRF-protected POST returns the expected response.
7. Verify one `ai_prefill.py` run succeeds on a temporary document copy.

## Production Deployment Checklist

1. Set production env vars on the host before startup.
2. Ensure `PORTAL_SECRET_KEY` is present. The app will fail fast if it is missing.
3. Ensure `GEMINI_API_KEY` is present. Chat and prefill will fail fast without it.
4. Install dependencies:

```powershell
& 'C:\morph-iq-portal\venv\Scripts\python.exe' -m pip install -r requirements.txt
```

5. Start the app with `FLASK_DEBUG` unset or `0`.
6. If using telemetry, set `SENTRY_DSN`.
7. Confirm secure cookies are enabled in production config.

## Post-Deploy Smoke Checklist

1. Open `/login`.
2. Sign in with a valid account.
3. Open `/ask-ai`.
4. Send one short chat prompt and confirm a non-error response.
5. Open a manager-scoped property list and confirm the client scope looks correct.
6. Check logs/Sentry for startup or request errors.

## Notes

- `Start_System_v2.bat` now loads all values from `.env` and prefers the local venv Python interpreter when available.
- `SENTRY_DSN` is optional for local work, but recommended before a public deployment.
- Treat any pasted or exposed API key as compromised and rotate it before deployment.
