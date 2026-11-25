#!/usr/bin/env python3
"""Flatten Tempo search results and expose total span counts for Grafana tables."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

TEMPO_URL = "http://tempo:3200"


def span_count(trace: dict) -> int:
    stats = trace.get("serviceStats") or {}
    total = sum(int((value or {}).get("spanCount") or 0) for value in stats.values())
    if total:
        return total
    span_set = trace.get("spanSet") or {}
    if span_set.get("matched") is not None:
        return int(span_set["matched"])
    return len(span_set.get("spans") or [])


def flatten(payload: dict) -> list[dict]:
    rows: list[dict] = []
    for trace in payload.get("traces") or []:
        start_ns = int(trace.get("startTimeUnixNano") or 0)
        rows.append(
            {
                "traceID": trace.get("traceID") or "",
                "service": trace.get("rootServiceName") or "",
                "name": trace.get("rootTraceName") or "",
                "startMs": start_ns / 1_000_000.0 if start_ns else None,
                "durationMs": trace.get("durationMs") or 0,
                "spans": span_count(trace),
            }
        )
    return rows


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/search", "/healthz"):
            self.send_error(404)
            return
        if parsed.path == "/healthz":
            self._write(200, b"ok", "text/plain")
            return

        query = parse_qs(parsed.query, keep_blank_values=True)
        params = [(key, value) for key, values in query.items() for value in values]
        url = f"{TEMPO_URL}/api/search"
        if params:
            url = f"{url}?{urlencode(params)}"

        try:
            with urlopen(url, timeout=30) as response:  # noqa: S310 - local Tempo only
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            body = json.dumps({"error": str(exc)}).encode()
            self._write(502, body, "application/json")
            return

        body = json.dumps(flatten(payload)).encode()
        self._write(200, body, "application/json")

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
