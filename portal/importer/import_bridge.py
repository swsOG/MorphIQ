"""Compatibility bridge module.

This module keeps the original import bridge entrypoint name and forwards to the
filesystem importer implemented in Phase 3.
"""

from .filesystem_importer import main


if __name__ == "__main__":
    raise SystemExit(main())
