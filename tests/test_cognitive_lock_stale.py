from __future__ import annotations

import os
import time
from pathlib import Path

from lib.cognitive_learner import _insights_lock


def test_insights_lock_clears_stale_lock_file(tmp_path: Path):
    lock = tmp_path / ".cognitive.lock"
    lock.write_text("stale", encoding="utf-8")
    # Make it look very old.
    old = time.time() - 3600
    os.utime(lock, (old, old))

    with _insights_lock(lock, timeout_s=0.05, stale_s=1.0) as guard:
        assert guard.acquired is True

