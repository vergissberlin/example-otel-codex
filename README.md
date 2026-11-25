# Codex-Telemetrie mit OpenTelemetry und Aspire

Dieses lokale Beispiel sendet Codex-Logs, -Metriken und -Traces per OTLP/gRPC an
einen OpenTelemetry Collector. Der Collector bearbeitet die Daten und leitet sie
an das Aspire Dashboard weiter:

`Codex (CLI oder Desktop-App) → Collector → Aspire Dashboard`

## Voraussetzungen

- Docker mit laufendem Docker-Daemon und Docker Compose.
- Eine aktuelle Codex CLI oder Codex in der ChatGPT-/Codex-Desktop-App mit
  Unterstützung für die `otel`-Konfiguration und Zugriff auf ein Codex-Konto.
- Freie lokale Ports 4317, 4318 und 18888 sowie Internetzugriff zum Laden der
  Container-Images und für Codex.

## Start

1. Im Repository-Verzeichnis den Collector und das Dashboard starten:

   ```sh
   docker compose up -d
   ```

2. Den Inhalt von [`codex/config.toml`](codex/config.toml) in die globale
   Codex-Konfiguration `~/.codex/config.toml` übernehmen (unter Windows:
   `%USERPROFILE%\.codex\config.toml`). Eine vorhandene Datei vorher sichern
   und die Einstellungen in einen bestehenden `[otel]`-Abschnitt integrieren,
   statt andere Einstellungen zu überschreiben. Bei abweichendem `CODEX_HOME`
   liegt die Datei dort. Die Desktop-App und die CLI verwenden diese gemeinsame
   Konfiguration; nach der Änderung die App vollständig neu starten.
3. Codex lokal verwenden und einen Prompt mit einer **fiktiven** E-Mail-Adresse
   eingeben, z. B. `Erkläre test@example.com als Beispiel`. Im Dashboard unter
   <http://localhost:18888> die Logs, Traces und Metriken des Codex-Dienstes
   ansehen. Die Ausgabe erfolgt gepuffert und kann etwas dauern. Je nach
   Codex-Version und Aktion werden unterschiedliche Signale erzeugt.

Zum Stoppen `docker compose down` ausführen. Die Dashboard-Daten sind
flüchtig und gehen beim Entfernen des Containers verloren. Zum Beenden des
Exports den hinzugefügten `[otel]`-Abschnitt wieder entfernen bzw. die
ursprüngliche Konfiguration wiederherstellen und Codex neu starten.

## Datenschutz und Grenzen

Für die Demonstration aktiviert `log_user_prompt = true` den Export von
Prompttexten. Der Collector ersetzt E-Mail-Adressen, die dem Beispielmuster
entsprechen, im `prompt`-Attribut von Logs und Span-Ereignissen durch
`[REDACTED_EMAIL]`. Die Verarbeitung findet **erst im Collector** statt:
Codex sendet den ursprünglichen Prompt an den lokalen Collector. Metriken
werden unverändert weitergeleitet.

Das ist **keine vollständige Anonymisierung**: andere personenbezogene Daten,
nicht erkannte E-Mail-Adressen und sensible Inhalte in anderen Attributen,
Logs, Traces oder Metriken bleiben möglicherweise erhalten. Keine echten
personenbezogenen Daten oder Geheimnisse für dieses Beispiel verwenden. Für
mehr Datenschutz `log_user_prompt = false` setzen; dann ist die Demonstration
der Prompt-Schwärzung nicht mehr sichtbar.

Der Collector und das Dashboard sind für eine lokale Demo ohne TLS und ohne
Authentifizierung eingerichtet. Die veröffentlichten Ports sind nur an
`127.0.0.1` gebunden; nicht unverändert öffentlich oder produktiv betreiben.
Das Dashboard empfängt OTLP nur über das interne Compose-Netzwerk.

## Fehlersuche

- `docker compose ps` und `docker compose logs collector aspire` zeigen den
  Containerstatus und Verbindungsfehler. Bei Portkonflikten die Belegung prüfen.
- Prüfen, ob die globale Konfiguration übernommen und Codex nach der Änderung
  neu gestartet wurde. Der Collector muss auf demselben Rechner erreichbar
  sein wie der Codex-Prozess (`127.0.0.1:4317`).
- Bei einem leeren Dashboard einen neuen Prompt ausführen und kurz warten;
  Metriken werden periodisch exportiert. Das Dashboard zeigt nur Daten seit
  seinem Start.

Weitere Informationen: [Codex-Konfiguration](https://developers.openai.com/codex/config-reference/),
[OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) und
[Aspire Dashboard](https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard/standalone).
