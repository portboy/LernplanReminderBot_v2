# **🎓 Lernplan Reminder Bot (v2) – Der Autonomie-Coach**

**Schluss mit dem täglichen Eltern-Kind-Streit ums Lernen.**

Dieser Telegram-Bot ist mehr als nur ein Wecker. Er ist ein digitaler Assistent, der Schülern hilft, ihren Tag selbstständig zu planen, und Eltern informiert hält, ohne dass sie "nerven" müssen.

## **🌟 Warum dieser Bot?**

Viele Eltern kennen das Problem: Man erinnert das Kind ans Vokabellernen, das Kind fühlt sich kontrolliert, die Stimmung kippt.

**Das Konzept dieses Bots ("The Autonomy Coach"):**

Statt starrer Befehle ("Lerne jetzt!") setzt dieser Bot auf **Selbstbestimmung**.

1. **Das Kind entscheidet morgens selbst**, *wann* es lernen möchte.
2. **Der Bot ist der neutrale Assistent**, der an die *eigene* Zusage erinnert.
3. **Gamification (Joker-System)** sorgt für Motivation und erlaubt legitime Pausen.
4. **Eltern werden passiv informiert** (durch weitergeleitete Sprachnachrichten), statt aktiv kontrollieren zu müssen.

## **🔄 Der Tagesablauf (The Core Loop)**

So fühlt sich die Nutzung für dein Kind an:

### **1️⃣ 07:30 Uhr – Der "Morning Prompt"**

Der Bot weckt nicht mit Aufgaben, sondern fragt: *"Guten Morgen! ☀️ Wie sieht dein Plan heute aus?"*

* Das Kind sieht die Fächer (z. B. Mathe, Englisch).
* **Action:** Das Kind wählt ein Fach und tippt auf eine Uhrzeit (z. B. 15:00 Uhr).
* **Oder:** Das Kind zieht einen **Joker** 🏖️ (1× pro Woche) und hat heute frei.

### **2️⃣ Der gewählte Zeitpunkt – Die Umsetzung**

Zur gewählten Zeit (z. B. 15:00 Uhr) meldet sich der Bot: *"🔔 Zeit für Mathe, wie besprochen!"*

* Das Kind lernt.
* **Action:** Statt langweiliger Checkboxen schickt das Kind einfach eine **Sprachnachricht** an den Bot: *"Habe 20 Minuten Brüche geübt."*
* **Feature:** Der Bot leitet diese Nachricht **sofort an die Eltern weiter**. Papa/Mama wissen Bescheid, ohne nachgefragt zu haben.

### **3️⃣ 20:00 Uhr – Der Check-in**

Der Tagesabschluss. *"Hast du heute alles geschafft?"*

* **Action:** Ja ✅ / Nein ❌.
* **Belohnung:** Bei Erfolg gibt es ein motivierendes Bild (z. B. Pferde, Memes).
* **Kein Druck:** Bei "Nein" gibt es kein Schimpfen, sondern ein aufmunterndes GIF.
* **Learning History:** Die tägliche Antwort wird archiviert und fließt in die Wochen-Statistik.

### **4️⃣ Sonntag 21:00 Uhr – Wochen-Statistik**

Eine automatische Zusammenfassung: Wie viele Tage gelernt? Welche Fächer? Gesamtzeit?

## **✨ Features im Überblick**

### **👶 Für das Kind (Student)**

* **Volle Kontrolle:** "Ich bestimme, wann ich lerne."
* **Joker-System:** Einmal pro Woche "frei" machen dürfen (wird Montags automatisch aufgefüllt).
* **Voice-First:** Erledigungen einfach per Sprachnachricht melden.
* **⏰ Zeiten verwalten:** Bis zu 3 Erinnerungszeiten über einen grafischen Stunden-/Minutenpicker einstellen — synchron zwischen Schüler und Eltern.
* **📊 Wochenübersicht:** Fächer, Minuten und geplante Tage auf einen Blick.
* **📈 Wochen-Statistik:** Persistente Lern-Historie über alle Tage hinweg.

### **👨‍👩‍👧 Für die Eltern (Parent)**

* **Entspannung:** Du musst nicht mehr drängeln. Der Bot übernimmt die Struktur.
* **Transparenz:** Du bekommst die Sprachnachrichten ("Habe Vokabeln gelernt") direkt weitergeleitet.
* **Tagesreport:** Um 20:00 Uhr erhältst du eine Zusammenfassung: Was war geplant? Was wurde erledigt?
* **Geteiltes Menü:** Erinnerungszeiten und Wochenpläne sind zwischen Schüler und Eltern synchronisiert.

## **🛠️ Technische Installation & Deployment**

Der Bot ist als **Docker-Container** konzipiert und läuft perfekt auf einem Home-Server (z. B. Unraid, Raspberry Pi, Synology).

### **Voraussetzungen**

1. Ein **Telegram Bot Token** (von [@BotFather](https://t.me/BotFather)).
2. Zwei Telegram-Accounts (Kind & Elternteil).
3. Docker & Docker Compose.

### **Option A: Schnellstart (Docker Compose)**

1. Repository klonen oder `docker-compose.yml`, `Dockerfile` und `src/` kopieren.
2. Konfiguration erstellen:

**`userconfig/bot_config.json`:**

```json
{
  "telegram_token": "DEIN_BOT_TOKEN",
  "student_chat_id": 123456789,
  "parent_chat_id": 987654321,
  "timezone": "Europe/Berlin",
  "log_level": "INFO",
  "allowed_subjects": [
    { "name": "Mathe", "emoji": "🔢" },
    { "name": "Englisch", "emoji": "🇬🇧" }
  ]
}
```

3. Starten:

```bash
docker compose up -d
```

> **Hinweis:** Die Konfiguration kann alternativ über Umgebungsvariablen (`TELEGRAM_TOKEN`, `STUDENT_CHAT_ID`, `PARENT_CHAT_ID` etc.) überschrieben werden. Die JSON-Datei hat Vorrang, Env-Vars überschreiben einzelne Werte daraus.

### **Option B: Unraid Server**

1. **Verzeichnisse erstellen:**
   ```bash
   mkdir -p /mnt/user/appdata/LernplanReminderBot/data
   mkdir -p /mnt/user/appdata/LernplanReminderBot/userconfig
   ```

2. **Konfiguration anlegen:**
   ```bash
   nano /mnt/user/appdata/LernplanReminderBot/userconfig/bot_config.json
   ```
   Inhalt: Siehe `bot_config.json` Beispiel oben.

3. **docker-compose.yml erstellen:**
   ```yaml
   services:
     lernplan-reminder-bot-v2:
       build: .
       container_name: lernplan-reminder-bot-v2
       restart: unless-stopped
       environment:
         - TZ=Europe/Berlin
       volumes:
         - ./data:/app/data
         - ./userconfig:/app/userconfig
         - /etc/localtime:/etc/localtime:ro
         - /etc/timezone:/etc/timezone:ro
       healthcheck:
         test: ["CMD", "python", "src/healthcheck.py"]
         interval: 60s
         timeout: 10s
         retries: 3
         start_period: 15s
   ```

4. **Container starten:**
   ```bash
   cd /mnt/user/appdata/LernplanReminderBot
   docker compose up -d
   ```

## **⚙️ Konfiguration**

### **1. Chat IDs ermitteln**

1. Sende mit dem Handy des **Kindes** `/start` an den Bot.
2. Sende mit dem Handy des **Elternteils** `/start` an den Bot.
3. Der Bot zeigt die Chat-ID direkt an: `Deine Chat-ID: 123456789`.
4. Trage diese IDs in `userconfig/bot_config.json` ein und starte den Container neu.

### **2. Konfigurationsreferenz (`bot_config.json`)**

| Feld | Pflicht? | Default | Beschreibung |
| :--- | :---: | :--- | :--- |
| `telegram_token` | ✅ | — | API Token vom BotFather |
| `student_chat_id` | ✅ | — | Chat-ID des Kindes |
| `parent_chat_id` | ❌ | `null` | Chat-ID der Eltern (für Weiterleitung) |
| `timezone` | ❌ | `Europe/Berlin` | Zeitzone |
| `log_level` | ❌ | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `allowed_subjects` | ❌ | Mathe, Englisch | Liste Fächer als `{name, emoji}` |
| `dynamic_planning_times` | ❌ | 07:30–20:30 | Auswahl-Uhrzeiten für die Morgenplanung |
| `duration_choices` | ❌ | 15–120 | Minutenoptionen bei der Wochenplanung |
| `max_reminder_times` | ❌ | `3` | Max. Erinnerungszeiten pro User |
| `morning_prompt_time` | ❌ | `07:30` | Uhrzeit der Morgen-Abfrage |
| `daily_check_time` | ❌ | `20:00` | Uhrzeit des Tagescheck-ins |
| `jokers_per_week` | ❌ | `1` | Joker pro Woche |

> **Env-Override:** Jedes Feld kann als Umgebungsvariable überschrieben werden: `TELEGRAM_TOKEN`, `STUDENT_CHAT_ID`, `PARENT_CHAT_ID`, `TIMEZONE`, `LOG_LEVEL`, `DATA_DIR`.

## **📋 Bot-Befehle**

| Befehl | Beschreibung |
| :--- | :--- |
| `/start` | Registrierung, zeigt Chat-ID |
| `/menu` | Hauptmenü öffnen |
| `/plan` | Wochenplan anzeigen |
| `/heute` | Heutige Aufgaben anzeigen |
| `/help` | Hilfetext |
| `/test` | Erinnerungsnachricht testen |
| `/testdaily` | 20-Uhr-Check manuell auslösen |

### **Menü-Buttons**

| Button | Funktion |
| :--- | :--- |
| 📅 Wochenplan bearbeiten | Fächer + Minuten pro Wochentag verwalten |
| 📊 Wochenübersicht | Ganzen Wochenplan mit Fächern und Zeiten anzeigen |
| ⏰ Zeiten verwalten | Erinnerungszeiten hinzufügen/löschen (Stunden-/Minutenpicker) |
| 📌 Heute anzeigen | Heutige Aufgaben + dynamische Einträge |
| 📈 Wochen-Statistik | Persistente Lern-Statistik der letzten 7 Tage |

## **🐛 Troubleshooting & FAQ**

| Symptom | Ursache | Lösung |
| :--- | :--- | :--- |
| **Bot antwortet gar nicht** | Falscher Token oder Container läuft nicht | `docker logs lernplan-reminder-bot-v2` prüfen |
| **20-Uhr Frage fehlt** | `student_chat_id` nicht gesetzt | In `bot_config.json` eintragen |
| **Keine Eltern-Info** | `parent_chat_id` nicht gesetzt | In `bot_config.json` ergänzen |
| **Daten weg nach Neustart** | Volume nicht korrekt gemountet | `./data:/app/data` prüfen |
| **Healthcheck unhealthy** | Config fehlt oder Telegram-API nicht erreichbar | `docker exec ... python src/healthcheck.py` manuell testen |
| **Statistik leer** | Erst nach Tagesabschluss (Ja/Nein) werden Daten archiviert | Mind. 1× den 20-Uhr-Check beantworten |

### **Updates einspielen**

```bash
docker compose pull
docker compose up -d
```

### **Backup**

Alle Daten liegen in `data/` als JSON-Dateien, Konfiguration in `userconfig/`.

```bash
tar -czf backup-$(date +%Y%m%d).tar.gz data/ userconfig/
```

## **🤖 Tech Stack**

| Komponente | Version | Zweck |
| :--- | :--- | :--- |
| Python | 3.12 | Runtime |
| python-telegram-bot | 21.4 | Telegram Bot Framework (async) |
| APScheduler | 3.10.4 | Job-Scheduling (Morning Prompt, Daily Check, Weekly Summary) |
| Pydantic | 2.8.2 | Konfigurationsvalidierung |
| Docker | Multi-Stage | Optimiertes Production-Image mit Non-Root-User |

### **Architektur**

```
src/
├── bot/main.py          # Entrypoint, Handler, BotContext
├── core/
│   ├── config.py        # Pydantic-Konfiguration (JSON + Env)
│   └── logging_config.py
├── models/settings.py   # UserSettings, DayPlan, SettingsRepository (atomare Writes)
├── services/__init__.py # LernplanService (Business Logic)
├── ui/
│   ├── keyboards.py     # Alle Telegram-Keyboards
│   └── messages.py      # Message-Builder & Formatter
└── healthcheck.py       # Docker HEALTHCHECK (Config + Data + API)
```

Siehe [ARCHITECTURE.md](ARCHITECTURE.md) für Details.

## **📄 Lizenz**

MIT License – Fühlt euch frei, den Bot für eure Familie anzupassen!
