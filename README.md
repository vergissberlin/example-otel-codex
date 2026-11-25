# Codex Telemetry with OpenTelemetry

This local example sends Codex logs, metrics, and traces via OTLP/gRPC to an
OpenTelemetry Collector. The collector redacts sample email addresses in prompt
attributes and forwards signals to a visualization frontend.

`Codex (CLI or desktop app) → Collector → Dashboard`

## Prerequisites

- Docker with a running daemon and Docker Compose.
- A current Codex CLI or Codex desktop app with `otel` config support and a
  Codex account.
- Free local ports for the stack you start (see table below) and network access
  to pull images and use Codex.

## Default stack: Aspire Dashboard

1. Start collector and dashboard:

   ```sh
   docker compose up -d
   ```

2. Merge [`codex/config.toml`](codex/config.toml) into the global Codex config
   `~/.codex/config.toml` (Windows: `%USERPROFILE%\.codex\config.toml`). Back up
   an existing file first and integrate into an existing `[otel]` section instead
   of overwriting other settings. If `CODEX_HOME` differs, use that path. Desktop
   and CLI share this config; fully restart the app after changing it.
3. Use Codex locally and send a prompt with a **fictional** email address, e.g.
   `Explain test@example.com as an example`. Open
   <http://localhost:18888>, find the Codex service signals, open the structured
   `codex.user_prompt` event, and check the `prompt` attribute. Export is buffered
   and may take a moment. Signals vary by Codex version and action.

Stop with `docker compose down`. Dashboard data is ephemeral. To stop exporting,
remove the added `[otel]` section (or restore the previous config) and restart
Codex.

## Alternative open-source dashboards

Only one stack should bind host ports `4317`/`4318` at a time. Stop the running
stack before starting another:

```sh
docker compose down
# or, for an alternative file:
docker compose -f compose.<name>.yaml down
```

| Compose file | Stack | UI | Signals |
| --- | --- | --- | --- |
| `compose.yaml` | Aspire Dashboard | <http://127.0.0.1:18888> | logs, metrics, traces |
| `compose.grafana.yaml` | Grafana + Tempo + Loki + Prometheus | <http://127.0.0.1:3200> | logs, metrics, traces |
| `compose.otel-lgtm.yaml` | Grafana otel-lgtm (all-in-one) | <http://127.0.0.1:3000> | logs, metrics, traces |
| `compose.jaeger.yaml` | Jaeger all-in-one | <http://127.0.0.1:16686> | traces (logs/metrics dropped) |
| `compose.zipkin.yaml` | Zipkin | <http://127.0.0.1:9411> | traces (logs/metrics dropped) |
| `compose.openobserve.yaml` | OpenObserve | <http://127.0.0.1:5080> | logs, metrics, traces |

Examples:

```sh
docker compose -f compose.grafana.yaml up -d
docker compose -f compose.jaeger.yaml up -d
docker compose -f compose.zipkin.yaml up -d
docker compose -f compose.openobserve.yaml up -d
docker compose -f compose.otel-lgtm.yaml up -d
```

Codex keeps exporting to `127.0.0.1:4317` in every stack; only the backend behind
the collector changes. Each stack uses the same prompt email redaction in the
collector.

### Notes per stack

- **Grafana (split):** Anonymous admin on port 3200. Datasources and three
  provisioned dashboards (Codex Overview, Traces, Logs) live under `grafana/`.
  Open <http://127.0.0.1:3200/dashboards> or jump to
  <http://127.0.0.1:3200/d/codex-overview>.   Trace tables include a Spans column (Tempo `serviceStats` via `traces-proxy`,
  scraped by Prometheus). The Trace waterfall panel shows the selected Trace ID
  inline — click a Trace ID or use the Trace ID dropdown. Codex services are
  typically `codex-app-server` and `codex-exec-server`. Traces become searchable
  a couple of seconds after spans finish.
- **otel-lgtm:** Single image with Loki, Grafana, Tempo, Mimir/Prometheus, and
  Alloy. Collector still sits in front for redaction.
- **Jaeger / Zipkin:** Classic trace UIs. Non-trace signals are accepted so Codex
  does not fail, then discarded (`nop` exporter).
- **OpenObserve:** Login `root@example.com` / `Complexpass#123` (local demo only).
  Data is stored in the `openobserve-data` volume.

Minimal one-container alternative without this repo's redaction collector:

```sh
docker run -d --rm \
  --name codex-telemetry \
  -p 127.0.0.1:3000:3000 \
  -p 127.0.0.1:4317:4317 \
  -p 127.0.0.1:4318:4318 \
  grafana/otel-lgtm:0.11.0
```

## Privacy and limits

For the demo, `log_user_prompt = true` exports prompt text. The collector replaces
email addresses matching the sample pattern in the `prompt` attribute of logs and
span events with `[REDACTED_EMAIL]`. Processing happens **only in the collector**:
Codex sends the original prompt to the local collector. Metrics are forwarded
unchanged.

This is **not full anonymization**: other personal data, unrecognized emails, and
sensitive content in other attributes, logs, traces, or metrics may remain. Do not
use real personal data or secrets for this example. For more privacy set
`log_user_prompt = false`; then the prompt-redaction demo is no longer visible.

Collector and dashboards are local demos without TLS or authentication (except
OpenObserve's demo login). Published ports bind to `127.0.0.1` only; do not run
unchanged on a public host or in production. Dashboards receive OTLP only on the
internal Compose network.

## Troubleshooting

- `docker compose -f <file> ps` and `docker compose -f <file> logs` show status and
  connection errors. Check port conflicts if a container fails to start.
- Confirm the global Codex config was applied and Codex was restarted. The
  collector must be reachable from the Codex process (`127.0.0.1:4317`).
- On an empty UI, send a new prompt and wait briefly; metrics export periodically.
  UIs only show data since their start.
- Trace-only UIs (Jaeger, Zipkin) will not show logs or metrics by design.

Further reading: [Codex configuration](https://developers.openai.com/codex/config-reference/),
[OpenTelemetry Collector](https://opentelemetry.io/docs/collector/),
[Aspire Dashboard](https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard/standalone),
[Grafana Tempo](https://grafana.com/docs/tempo/),
[Jaeger](https://www.jaegertracing.io/),
[Zipkin](https://zipkin.io/),
[OpenObserve](https://openobserve.ai/docs/).
