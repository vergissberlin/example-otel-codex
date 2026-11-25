#!/usr/bin/env python3
"""Expose Tempo search hits (incl. span counts) as Prometheus metrics for Grafana tables."""

from __future__ import annotations

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

TEMPO_URL = "http://tempo:3200"
DEFAULT_LOOKBACK_SECONDS = 6 * 60 * 60
DEFAULT_LIMIT = 50


def span_count(trace: dict) -> int:
    stats = trace.get("serviceStats") or {}
    total = sum(int((value or {}).get("spanCount") or 0) for value in stats.values())
    if total:
        return total
    span_set = trace.get("spanSet") or {}
    if span_set.get("matched") is not None:
        return int(span_set["matched"])
    return len(span_set.get("spans") or [])


def fetch_traces(start: int, end: int, limit: int, query: str) -> list[dict]:
    params = [
        ("start", str(start)),
        ("end", str(end)),
        ("limit", str(limit)),
        ("q", query),
    ]
    url = f"{TEMPO_URL}/api/search?{urlencode(params)}"
    print(f"traces-proxy -> {url}", file=sys.stderr, flush=True)
    with urlopen(url, timeout=30) as response:  # noqa: S310 - local Tempo only
        payload = json.load(response)
    rows: list[dict] = []
    for trace in payload.get("traces") or []:
        start_ns = int(trace.get("startTimeUnixNano") or 0)
        rows.append(
            {
                "trace_id": trace.get("traceID") or "",
                "service": trace.get("rootServiceName") or "",
                "name": trace.get("rootTraceName") or "",
                "start_ms": int(start_ns / 1_000_000) if start_ns else 0,
                "duration_ms": int(trace.get("durationMs") or 0),
                "spans": span_count(trace),
            }
        )
    print(f"traces-proxy <- {len(rows)} rows", file=sys.stderr, flush=True)
    return rows


def prom_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def render_prometheus(rows: list[dict]) -> bytes:
    lines = [
        "# HELP trace_spans Number of spans in a Tempo trace from the latest search.",
        "# TYPE trace_spans gauge",
    ]
    for row in rows:
        labels = ",".join(
            [
                f'trace_id="{prom_escape(row["trace_id"])}"',
                f'service="{prom_escape(row["service"])}"',
                f'name="{prom_escape(row["name"])}"',
                f'duration_ms="{row["duration_ms"]}"',
                f'start_ms="{row["start_ms"]}"',
            ]
        )
        lines.append(f"trace_spans{{{labels}}} {row['spans']}")
    lines.append("")
    return ("\n".join(lines)).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._write(200, b"ok", "text/plain")
            return
        if parsed.path not in ("/", "/metrics", "/search"):
            self.send_error(404)
            return

        query = parse_qs(parsed.query, keep_blank_values=True)
        now = int(time.time())
        start = now - DEFAULT_LOOKBACK_SECONDS
        end = now
        limit = DEFAULT_LIMIT
        q = "{}"

        if query.get("start") and query["start"][0].isdigit():
            start = int(query["start"][0])
        if query.get("end") and query["end"][0].isdigit():
            end = int(query["end"][0])
        if query.get("limit") and query["limit"][0].isdigit():
            limit = int(query["limit"][0])
        if query.get("q") and query["q"][0]:
            q = query["q"][0]

        if end <= start:
            start = now - DEFAULT_LOOKBACK_SECONDS
            end = now

        try:
            rows = fetch_traces(start, end, limit, q)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            body = json.dumps({"error": str(exc)}).encode()
            self._write(502, body, "application/json")
            return

        if parsed.path == "/search":
            self._write(200, json.dumps(rows).encode(), "application/json")
            return

        self._write(200, render_prometheus(rows), "text/plain; version=0.0.4; charset=utf-8")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
