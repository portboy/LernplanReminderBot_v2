## Architekturübersicht — LernplanReminderBot

Unten sind zwei Darstellungen: ein Komponenten‑Diagramm (Mermaid) und ein Sequenzdiagramm für einen typischen Ablauf.

---

### Komponenten (Mermaid)

```mermaid
flowchart TD
  User["Parent / Student (Telegram)"]
  TelegramAPI["Telegram API"]
  BotApp["LernplanReminderBot\n(src/bot/main.py)"]
  Handlers["Command & Callback Handlers\n/start /menu /addzeit /plan ..."]
  Scheduler["JobQueue / APScheduler\n(scheduling, 20:00-Query, reminders)"]
  Repo["SettingsRepository\n(src/models/settings.py)\ndata/user_<chat_id>.json"]
  Media["Horse images / GIFs"]
  Docker["Deployment (.env, Docker / GHCR)"]

  User -->|Messages / Button| TelegramAPI --> BotApp
  BotApp --> Handlers
  Handlers -->|load/save| Repo
  Handlers -->|update schedule| Scheduler
  Scheduler -->|trigger jobs| BotApp
  BotApp -->|send messages| TelegramAPI --> User
  BotApp --> Media
  Docker -->|env: TELEGRAM_TOKEN, PARENT_CHAT_ID, STUDENT_CHAT_ID| BotApp
  Repo -->|persist| Docker
```

---

### Sequenzdiagramm (Mermaid) — Beispiel: Nutzer fügt eine Erinnerungszeit hinzu

```mermaid
sequenceDiagram
  autonumber
  participant U as User (Telegram)
  participant T as Telegram API
  participant B as BotApp (`src/bot/main.py`)
  participant H as Handlers (commands/callbacks)
  participant R as Repo (JSON files)
  participant S as Scheduler (JobQueue)

  U->>T: Klick /send message `/addzeit 08:00` oder Button
  T->>B: Update (Webhook/LongPoll)
  B->>H: CommandHandler (/addzeit)
  H->>R: load(chat_id)
  R-->>H: UserSettings
  H-->>R: save(updated reminder_times)
  R-->>H: ok
  H->>S: schedule_all_reminders() (aktualisiert Jobs)
  S-->>B: Job geplant
  H->>T: Antwort: "Zeit hinzugefügt"
  T-->>U: Nachricht angezeigt

  Note over S,B: Später — Trigger durch Scheduler
  S->>B: reminder job fires
  B->>T: send reminder message
  T->>U: Reminder arrives
```

---

Kurz (Datei‑/Modulzuordnung)
- `src/bot/main.py` – Bot‑Entrypoint, Handler, UI‑Logik, Message Builder, Scheduler‑Integration
- `src/models/settings.py` – `UserSettings`, `DayPlan`, `SettingsRepository` (JSON‑Persistenz)
- `src/core/logging_config.py` – Logging Setup
- `data/` – Persistente JSON Dateien (`user_<chat_id>.json`)
- `pyproject.toml` – Abhängigkeiten (python-telegram-bot, APScheduler, python-dotenv)

Deployment‑Hinweis
- Konfiguration via `.env` (z. B. `TELEGRAM_TOKEN`, `PARENT_CHAT_ID`, `STUDENT_CHAT_ID`, `DATA_DIR`).
- Docker / docker-compose für Headless Betrieb; mount von `data/` für Persistenz.

---

Wenn du willst, lege ich diese Datei als `ARCHITECTURE.md` ab (erledigt) und kann zusätzlich ein Sequence‑Diagramm für die 20:00‑Abfrage oder das Merge‑/Sync‑Verhalten zwischen Eltern/Schüler erzeugen.
