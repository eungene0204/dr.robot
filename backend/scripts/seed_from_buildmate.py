"""Import the pipeline's published catalog snapshot into PostgreSQL.

The server does this automatically when the snapshot changes; run this to force it
or to import a specific file.

    uv run python scripts/seed_from_buildmate.py [catalog.json | documents.db]
"""

from __future__ import annotations

import sys
from pathlib import Path

from pcquote import importer
from pcquote.db import create_schema, session_factory

# Re-exported for tests and older callers.
ssd_interface = importer.ssd_interface

if __name__ == "__main__":
    create_schema()
    with session_factory()() as s:
        if len(sys.argv) > 1:
            print(importer.import_snapshot(s, importer.load_snapshot_path(Path(sys.argv[1]))))
        else:
            print(importer.sync(s, force=True))
