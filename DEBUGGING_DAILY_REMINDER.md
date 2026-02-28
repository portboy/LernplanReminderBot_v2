# Debugging Daily Reminder Issues

Dieses Dokument erklärt, wie man Probleme mit der täglichen 20:00-Uhr-Erinnerung debuggt.

## Überblick

Das tägliche Check-ins System besteht aus:

1. **Morning Prompt** (configurable, default 07:30) — Fragt: "Wie sieht dein Plan heute aus?"
2. **Dynamische Erinnerungen** — Zur gewählten Uhrzeit wird erinnert
3. **Daily Check** (configurable, default 20:00) — Fragt: "Hast du heute gelernt?"
4. **Antwort-Handling** — Ja/Nein → Archivierung in `learning_history`
5. **Eltern-Benachrichtigung** — Parent erhält Antwort und Tagesreport
6. **Weekly Summary** (Sonntag 21:00) — Statistik der Woche

## Architektur-Kontext

Alle Jobs laufen über `APScheduler`/`JobQueue` und nutzen den `BotContext` aus `application.bot_data["ctx"]`:

```
BotContext
├── config        → BotConfig (student_chat_id, parent_chat_id, daily_check_time, ...)
├── service       → LernplanService (archive_daily_to_history, get_weekly_statistics, ...)
├── repo          → SettingsRepository (load, save — atomare JSON-Writes)
├── keyboards     → KeyboardBuilder
└── messages      → MessageBuilder
```

## Häufige Probleme & Lösungen

### 1. Daily Reminder wird nicht gesendet

**Symptome**: Um 20:00 passiert nichts.

**Prüfen:**

```bash
docker logs lernplan-reminder-bot-v2 | grep -i "daily_check\|schedule"
```

**Mögliche Ursachen:**

| Log-Meldung | Ursache | Lösung |
| :--- | :--- | :--- |
| `Student chat ID not configured` | `student_chat_id` fehlt | In `bot_config.json` eintragen |
| `Scheduled daily check at 20:00` fehlt | Bot wurde nach 20:00 gestartet | Neustart vor 20:00 oder `/testdaily` |
| Kein Log zum Zeitpunkt | Container war gestoppt | `docker ps` → Uptime prüfen |

**Lösung:**

```bash
# Prüfe Konfiguration:
docker exec lernplan-reminder-bot-v2 cat /app/userconfig/bot_config.json | grep student_chat_id
```

### 2. Eltern erhalten keine Benachrichtigung

**Symptome**: Schüler bekommt die Frage, Eltern bekommen nichts.

**Prüfen:**

```bash
docker logs lernplan-reminder-bot-v2 | grep -i "parent"
```

| Log-Meldung | Bedeutung |
| :--- | :--- |
| `PARENT_CHAT_ID not set` oder `parent_chat_id: null` | Nicht konfiguriert |
| `parent notifications disabled` | Warning beim Start |

**Lösung:**

In `userconfig/bot_config.json`:
```json
{
  "parent_chat_id": 987654321
}
```

Container neu starten.

### 3. Antwort-Buttons (Ja/Nein) funktionieren nicht

**Symptome**: Schüler kann Buttons klicken, aber nichts passiert.

**Prüfen:**

```bash
docker logs lernplan-reminder-bot-v2 | grep "on_learned_response"
```

**Erwartete Logs:**

```
on_learned_response: 'learned_yes' from chat 123456789
```

Wenn kein Log erscheint: Handler nicht registriert → Bot neu bauen und deployen.

### 4. Statistik bleibt leer

**Symptome**: `📈 Wochen-Statistik` zeigt "Keine abgeschlossenen Lerneinheiten".

**Ursache**: `archive_daily_to_history()` wird erst aufgerufen, wenn der Schüler auf Ja/Nein klickt. Wenn die Frage nie beantwortet wird, wird nichts archiviert.

**Prüfen:**

```bash
# Direkt in die User-Datei schauen:
docker exec lernplan-reminder-bot-v2 cat /app/data/user_123456789.json | python -m json.tool | grep -A5 learning_history
```

**Lösung**: Mindestens 1× den 20-Uhr-Check beantworten. Oder manuell testen mit `/testdaily`.

## Manuelles Testen

### Daily Check manuell auslösen

```
/testdaily
```

Dieser Befehl ruft `daily_check()` direkt auf:
1. Schüler erhält die "Hast du gelernt?"-Frage mit Ja/Nein-Buttons
2. Eltern erhalten Info, dass die Frage gesendet wurde
3. Auf Ja/Nein-Klick wird `archive_daily_to_history()` aufgerufen

### Erinnerungsnachricht testen

```
/test
```

Zeigt die Erinnerungsnachricht für heute (basierend auf Wochenplan + dynamische Einträge).

## Log-Referenz

### Scheduling-Logs (beim Start)

| Nachricht | Bedeutung |
| :--- | :--- |
| `Scheduled morning prompt at 07:30` | Morgen-Job geplant |
| `Scheduled daily check at 20:00` | Tagescheck geplant |
| `Scheduled weekly summary for Sundays 21:00` | Wochenstatistik geplant |
| `Student chat ID not configured — skipping system jobs` | Kein Student konfiguriert |

### Daily Check Logs

| Nachricht | Bedeutung |
| :--- | :--- |
| `daily_check: Starting...` | Funktion ausgelöst |
| `daily_check: Error...` | Fehler aufgetreten |

### Learned Response Logs

| Nachricht | Bedeutung |
| :--- | :--- |
| `on_learned_response: 'learned_yes' from chat X` | Schüler hat "Ja" geklickt |
| `on_learned_response: 'learned_no' from chat X` | Schüler hat "Nein" geklickt |

### Archive Logs

| Nachricht | Bedeutung |
| :--- | :--- |
| `Archived N entries to history for chat X` | N Einträge in learning_history gespeichert |

## Datenstruktur

Die `learning_history` eines Users sieht so aus (in `data/user_<id>.json`):

```json
{
  "learning_history": [
    {
      "date_iso": "2026-02-27",
      "weekday": "freitag",
      "subject": "Mathe",
      "planned_minutes": 30,
      "source": "week_plan",
      "learned_response": "yes",
      "timestamp": "2026-02-27T20:01:23+01:00"
    }
  ]
}
```

Felder:
- `date_iso` — Datum im ISO-Format
- `weekday` — Wochentag (deutsch, lowercase)
- `subject` — Fach
- `planned_minutes` — Geplante Minuten (aus Wochenplan)
- `source` — `"week_plan"` oder `"dynamic"`
- `learned_response` — `"yes"` oder `"no"`
- `timestamp` — Zeitpunkt der Archivierung
