#!/usr/bin/env python3
"""stdin_ingest — universal adapter

Reads newline-delimited SparkEventV1 JSON objects from stdin and POSTs them to sparkd.

This is a compatibility escape hatch: any environment that can run a shell command can
feed Spark, without writing a bespoke adapter.

Usage:
  python3 adapters/stdin_ingest.py --sparkd http://127.0.0.1:8787 < events.ndjson

Auth:
  - If sparkd is protected, pass --token or set SPARKD_TOKEN.
"""

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen


def post(url: str, obj: dict, token: str = None):
    data = json.dumps(obj).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method="POST")
    with urlopen(req, timeout=10) as resp:
        resp.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sparkd", default="http://127.0.0.1:8787", help="sparkd base URL")
    ap.add_argument("--token", default=None, help="sparkd token (or set SPARKD_TOKEN env)")
    args = ap.parse_args()

    token = args.token or os.environ.get("SPARKD_TOKEN")
    ingest_url = args.sparkd.rstrip("/") + "/ingest"

    ok = 0
    bad = 0
    first_error = None
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            post(ingest_url, obj, token=token)
            ok += 1
        except Exception as e:
            bad += 1
            if first_error is None:
                first_error = e
            try:
                meta = {}
                if isinstance(obj, dict):
                    for k in ("source", "kind", "session_id", "trace_id"):
                        if obj.get(k) is not None:
                            meta[k] = obj.get(k)
                meta_str = f" meta={meta}" if meta else ""
                sys.stderr.write(f"[stdin_ingest] post failed: {type(e).__name__}: {e}{meta_str}\n")
            except Exception:
                pass

    # Counts are useful when running manually; errors go to stderr.
    if sys.stdout.isatty():
        print(f"sent={ok} bad={bad}")
    if bad and not sys.stderr.isatty():
        sys.stderr.write(f"[stdin_ingest] errors: {bad} (first: {type(first_error).__name__}: {first_error})\n")


if __name__ == "__main__":
    main()
