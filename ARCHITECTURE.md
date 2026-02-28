## Architekturübersicht — LernplanReminderBot v2

### Modulstruktur

```
src/
├── bot/
│   └── main.py              # Entrypoint, Handler, BotContext, Scheduler
├── core/
│   ├── config.py            # Pydantic-basierte Konfiguration (JSON + Env)
│   └── logging_config.py    # Logging Setup
├── models/
│   └── settings.py          # UserSettings, DayPlan, SettingsRepository
├── services/
│   └── __init__.py          # LernplanService (Business Logic)
├── ui/
│   ├── keyboards.py         # KeyboardBuilder (alle Telegram-Keyboards)
│   └── messages.py          # MessageBuilder (Textformatierung)
└── healthcheck.py           # Docker HEALTHCHECK Script

tests/
├── test_config.py           # BotConfig Validierung & load_config
├── test_shared_functionality.py  # Service-Layer: Reminder, Sync, History
└── test_weekly_overview_improvements.py  # Messages, Statistik, UI

data/                        # Persistente JSON-Dateien (user_<chat_id>.json)
userconfig/
└── bot_config.json          # Konfiguration (im Container gemountet)
```

---

### Schichtenarchitektur

```
┌─────────────────────────────────────────────────────────┐
│  Telegram API                                           │
└────────┬────────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────────────────┐
│  bot/main.py                                            │
│  ┌─────────────┐  ┌───────────────┐  ┌───────────────┐ │
│  │ Handlers    │  │ BotContext    │  │ Scheduler     │ │
│  │ (Commands,  │  │ (Dataclass)  │  │ (APScheduler  │ │
│  │  Callbacks, │  │              │  │  JobQueue)    │ │
│  │  Text/Voice)│  │              │  │              │ │
│  └──────┬──────┘  └──────┬───────┘  └──────────────┘ │
└─────────┼────────────────┼──────────────────────────────┘
          │                │
          │   ┌────────────▼────────────┐
          │   │ BotContext hält:        │
          │   │ • config: BotConfig     │
          │   │ • repo: SettingsRepo    │
          │   │ • service: LernplanSvc  │
          │   │ • keyboards: KBBuilder  │
          │   │ • messages: MsgBuilder  │
          │   └────────────┬────────────┘
          │                │
┌─────────▼────────────────▼──────────────────────────────┐
│  services/__init__.py — LernplanService                 │
│  (Business Logic: Sync, Reminder, History, Statistics)  │
└────────┬────────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────────────────┐
│  models/settings.py — SettingsRepository                │
│  (Atomare JSON-Persistenz: tempfile + os.replace)       │
└─────────────────────────────────────────────────────────┘
```

---

### Komponenten-Diagramm (Mermaid)

```mermaid
flowchart TD
  User["Parent / Student\n(Telegram App)"]
  TelegramAPI["Telegram Bot API"]
  BotApp["bot/main.py\nBotContext + Handler"]
  Config["core/config.py\nBotConfig (Pydantic)\nJSON + Env Vars"]
  Service["services/\nLernplanService\n(Sync, History, Stats)"]
  UI_KB["ui/keyboards.py\nKeyboardBuilder"]
  UI_MSG["ui/messages.py\nMessageBuilder"]
  Repo["models/settings.py\nSettingsRepository\n(Atomare JSON-Writes)"]
  Scheduler["APScheduler JobQueue\n(Morning, DailyCheck,\nWeekly, Dynamic)"]
  Health["healthcheck.py\n(Config + Data + API)"]
  Docker["Docker Container\n(Multi-Stage, Non-Root)"]
  Data["data/user_*.json"]
  UserConfig["userconfig/bot_config.json"]

  User -->|Messages / Buttons| TelegramAPI --> BotApp
  BotApp --> Service
  BotApp --> UI_KB
  BotApp --> UI_MSG
  Service --> Repo
  Repo --> Data
  Config --> UserConfig
  BotApp --> Config
  BotApp --> Scheduler
  Scheduler -->|Jobs auslösen| BotApp
  BotApp -->|Nachrichten senden| TelegramAPI --> User
  Docker --> BotApp
  Docker --> Health
  Health --> Config
  Health --> Data
```

---

### Sequenzdiagramm — Erinnerungszeit hinzufügen

```mermaid
sequenceDiagram
  autonumber
  participant U as User (Telegram)
  participant T as Telegram API
  participant B as bot/main.py
  participant S as LernplanService
  participant R as SettingsRepository

  U->>T: Klick "⏰ Zeiten verwalten"
  T->>B: CallbackQuery "menu_times"
  B->>S: get_shared_reminder_times()
  S->>R: load(chat_id)
  R-->>S: UserSettings
  S-->>B: aktuelle Zeiten
  B->>T: Zeiten-Menü anzeigen
  T-->>U: Menü mit Zeiten + "➕ Hinzufügen"

  U->>T: Klick "➕ Hinzufügen"
  T->>B: CallbackQuery "add_time"
  B->>T: Stundenpicker (0–23)
  T-->>U: Stunden-Grid

  U->>T: Klick "14"
  T->>B: CallbackQuery "pick_hour_14"
  B->>T: Minutenpicker (00–55)
  T-->>U: Minuten-Grid

  U->>T: Klick "30"
  T->>B: CallbackQuery "pick_minute_14_30"
  B->>S: add_reminder_time(chat_id, "14:30", ...)
  S->>R: load + save (beide User)
  R-->>S: ok
  S-->>B: (True, "✅ Erinnerung um 14:30 hinzugefügt.")
  B->>B: schedule_all_reminders()
  B->>T: Aktualisiertes Zeiten-Menü
  T-->>U: Menü zeigt 14:30
```

---

### Sequenzdiagramm — 20-Uhr Tagescheck

```mermaid
sequenceDiagram
  autonumber
  participant Sched as APScheduler
  participant B as bot/main.py
  participant S as LernplanService
  participant R as SettingsRepository
  participant T as Telegram API
  participant Student as Schüler
  participant Parent as Eltern

  Sched->>B: daily_check() um 20:00
  B->>R: load(student_chat_id)
  R-->>B: UserSettings
  B->>T: "Hast du heute gelernt?" + Ja/Nein Keyboard
  T-->>Student: Frage angezeigt
  B->>T: Info an Eltern: "20-Uhr-Abfrage gesendet"
  T-->>Parent: Info-Nachricht

  Student->>T: Klick "Ja ✅"
  T->>B: CallbackQuery "learned_yes"
  B->>S: archive_daily_to_history(chat_id, "yes")
  S->>R: load → append learning_history → save
  B->>T: Motivationsbild 🐴🎉
  T-->>Student: Bild angezeigt
  B->>T: Kommentar-Frage
  T-->>Student: "Möchtest du noch was sagen?"
  B->>T: Info an Eltern: "JA gelernt ✅"
  T-->>Parent: Antwort angezeigt
```

---

### Schlüssel-Designentscheidungen

| Entscheidung | Begründung |
| :--- | :--- |
| **BotContext Dataclass** statt globaler Variablen | Testbarkeit, kein verstreuter State, klare Abhängigkeiten |
| **LernplanService** als eigene Schicht | Business Logic von Handler-Code getrennt; testbar ohne Telegram-Mocking |
| **Pydantic BotConfig** mit JSON + Env-Override | Typsichere Validierung, flexible Konfiguration für Docker + lokale Entwicklung |
| **Atomare JSON-Writes** (`tempfile` + `os.replace`) | Kein Datenverlust bei Crash/Stromausfall während des Schreibens |
| **`learning_history`** Feld in UserSettings | Statistik überlebt das tägliche Löschen des `daily_dynamic_plan` |
| **Shared State** zwischen Student + Parent | Erinnerungszeiten und Wochenpläne sind immer synchron |
| **Multi-Stage Docker Build** + Non-Root User | Kleineres Image, Security Best Practice |
| **`zoneinfo`** statt `pytz` | Stdlib ab Python 3.9, kein Extra-Dependency |
| **Grafischer Stunden-/Minutenpicker** | Benutzerfreundlicher als Texteingabe "/addzeit HH:MM" |
