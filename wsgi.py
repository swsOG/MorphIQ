"""Production WSGI entrypoint for the MorphIQ Portal.

Run behind a real WSGI server instead of the Flask dev server, e.g.:

    gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app      # then put TLS-terminating nginx in front

Never run the Flask dev server or FLASK_DEBUG=1 in production (finding M-3).
PORTAL_SECRET_KEY must be a strong, unique value (finding C-4) — the app refuses
to start otherwise.
"""
from portal_new.app import app  # noqa: F401

if __name__ == "__main__":
    app.run()
