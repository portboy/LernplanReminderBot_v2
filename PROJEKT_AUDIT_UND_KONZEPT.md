# Projekt-Audit & Weiterentwicklungskonzept

**LernplanReminderBot v2**
**Datum:** 27. Februar 2026
**Autor:** Senior IT-Entwicklungsleiter / Architekt
**Scope:** Vollständige Projektprüfung, Audit & Roadmap

---

## 1. Einsatzweck-Analyse

### 1.1 Zielgruppe & Kontext

| Aspekt | Beschreibung |
|--------|-------------|
| **Primäre Nutzer** | Schüler (1 Person) + Elternteil (1 Person) |
| **Kanal** | Telegram Messenger |
| **Kernproblem** | Schüler brauchen Struktur beim täglichen Lernen; Eltern wollen Einblick und Kontrolle |
| **Lösung** | Automatisierte Erinnerungen, gemeinsamer Wochenplan, tägliches Feedback-System |

### 1.2 Funktionsumfang (IST-Zustand)

| Feature | Status | Bewertung |
|---------|--------|-----------|
| Wochenplan (Fach + Minuten/Tag) | ✅ Implementiert | Solide Grundfunktion |
| Geteilter State Eltern ↔ Schüler | ✅ Implementiert | Gut umgesetzt, beide sehen identische Daten |
| Morgen-Prompt (07:30) | ✅ Implementiert | Dynamische Fachauswahl + Zeitwahl |
| Abend-Check (20:00) | ✅ Implementiert | Ja/Nein-Frage + optionaler Kommentar |
| Joker-System | ✅ Implementiert | 1 Joker/Woche, wöchentlicher Reset |
| Sprachnachrichten-Weiterleitung | ✅ Implementiert | Schüler→Eltern |
| Wochenübersicht | ✅ Implementiert | Farbkodiert, mit Zusammenfassung |
| Dynamische Tagesplanung | ✅ Implementiert | Spontane Lernblöcke hinzufügen |
| Wochen-Statistik | ⚠️ Fehlerhaft | Daten werden täglich gelöscht → immer leer |
| Erinnerungszeiten-Verwaltung | ❌ Fehlt im neuen Code | War im Legacy vorhanden, fehlt in `main_new.py` |

### 1.3 Bewertung des Nutzens

Der Bot adressiert ein reales Bedürfnis: **Lernorganisation für Schüler mit elterlicher Begleitung**. Die Telegram-Plattform ist klug gewählt – kein App-Download, keine Extra-Registrierung, direkt im Messenger des Schülers präsent.

**Stärken des Konzepts:**
- Niedrige Einstiegshürde (nur `/start` im Telegram-Chat)
- Geteilte Verantwortung (Eltern sehen sofort Änderungen)
- Motivationselemente (Pferde-Bilder bei Erfolg, traurige GIFs bei Misserfolg)
- Joker-System als "Ventil" für stressige Tage

**Schwächen des Konzepts:**
- Nur 2-Personen-Modell (1 Schüler, 1 Elternteil) – nicht skalierbar
- Kein Lernfortschritt über Zeit sichtbar (History fehlt)
- Feedback binär (Ja/Nein) – keine Nuancierung
- Kein Belohnungssystem über den Joker hinaus

---

## 2. Technisches Audit

### 2.1 Architektur-Bewertung

```
┌─────────────────────────────────────────────────┐
│  Architektur-Qualität      ████████░░  8/10     │
│  Code-Qualität             ███████░░░  7/10     │
│  Sicherheit                ████░░░░░░  4/10     │
│  Testabdeckung             █████░░░░░  5/10     │
│  Deployment & DevOps       ████████░░  8/10     │
│  Datenpersistenz           █████░░░░░  5/10     │
│  User Experience           ██████░░░░  6/10     │
├─────────────────────────────────────────────────┤
│  GESAMT                    █████████░  6.1/10   │
└─────────────────────────────────────────────────┘
```

### 2.2 Stärken (Was gut gemacht ist)

#### ✅ Saubere Schichtenarchitektur
Die Trennung in `bot/` → `services/` → `models/` → `ui/` ist vorbildlich. Der Service-Layer (`LernplanService`) kapselt Business-Logik sauber von Handler-Code. Die UI-Module (`KeyboardBuilder`, `MessageBuilder`) sind wiederverwendbar und testbar.

#### ✅ Konfigurationsmanagement
Die Pydantic-basierte `BotConfig` mit JSON-Datei + Environment-Variable-Override ist professionell umgesetzt. Fächer, Zeiten und Medien sind ohne Code-Änderung konfigurierbar.

#### ✅ Docker & CI/CD
Multi-Stage Build, Non-Root User, Health-Checks, Volume-Mounts und GitHub Actions für Tests/Linting bilden eine solide DevOps-Basis.

#### ✅ Validierung
Pydantic-Validatoren für Chat-IDs, Zeitformate, Log-Levels und Minutenzahlen fangen Fehlkonfigurationen früh ab.

#### ✅ Anonymisierung
SHA256-gehashte Dateinamen statt Klartext-Chat-IDs in der Persistenz sind ein durchdachtes Privacy-Feature.

### 2.3 Kritische Befunde

#### 🔴 KRITISCH: Telegram-Token im Git-Repository

**Datei:** `userconfig/bot_config.json`, Zeile 2
```json
"telegram_token": "8463260162:AAEBMfZ_gVYdUusVeeURGHr_nv44bT9nUmo"
```

**Risiko:** Jeder mit Zugriff auf das Repository kann den Bot übernehmen, Nachrichten lesen und als Bot agieren. Der Token muss **sofort** über BotFather `/revoke` rotiert und ausschließlich über `.env` oder Docker Secrets verwaltet werden.

**Empfehlung:** `bot_config.json` darf nur Template-Werte enthalten. Echte Credentials gehören in `.env` (bereits in `.gitignore`).

---

#### 🔴 KRITISCH: Legacy-Code parallel zum Produktivcode

| Datei | Zeilen | Status |
|-------|--------|--------|
| `src/bot/main.py` | 1116 | Legacy — wird nicht verwendet |
| `src/bot/main_new.py` | 945 | Aktiv — Dockerfile CMD zeigt hierhin |

**Problem:**
- Tests in `test_shared_functionality.py` und `test_weekly_overview_improvements.py` patchen `bot.main` (Legacy!), nicht `bot.main_new`
- Zwei divergierende Implementierungen verursachen Verwirrung
- Legacy enthält Features (z.B. Zeiten-Verwaltung), die im neuen Code fehlen

**Empfehlung:** `main.py` archivieren oder entfernen. Alle Tests auf `main_new.py` migrieren.

---

#### 🟠 HOCH: Wochen-Statistik ist funktionslos

In `daily_check()` (main_new.py, ca. Zeile 580):
```python
# Clear dynamic plan
settings.daily_dynamic_plan = []
repo.save(settings)
```

Alle dynamischen Einträge werden **jeden Abend gelöscht**. Die Wochen-Statistik (`get_weekly_statistics()`) iteriert über genau diese Einträge und liefert daher **immer leere Ergebnisse**.

**Empfehlung:** Einführung eines `learning_history`-Feldes, das abgeschlossene Einträge dauerhaft speichert, bevor die Tagesdaten gelöscht werden.

---

#### 🟠 HOCH: Erinnerungszeiten-Verwaltung fehlt

Das Hauptmenü in `main_new.py` bietet:
- 📅 Wochenplan bearbeiten
- 📊 Wochenübersicht
- 📌 Heute anzeigen
- 📈 Wochen-Statistik
- 🔄 Schließen

Die Verwaltung von Erinnerungszeiten (Hinzufügen/Entfernen von Reminder-Zeiten) fehlt komplett. Im Legacy-Code (`main.py`) war diese Funktion unter "⏰ Zeiten verwalten" implementiert.

---

#### 🟠 HOCH: Health-Check prüft nicht den Bot

```dockerfile
HEALTHCHECK CMD python -c "import sys; sys.exit(0)"
```

Dieser Check verifiziert nur, dass Python startet – nicht ob der Bot verbunden ist oder Telegram erreichbar ist.

---

#### 🟡 MITTEL: Keine atomaren Schreibvorgänge

`SettingsRepository.save()` schreibt direkt in die JSON-Datei. Ein Absturz während des Schreibens kann die Datei korrumpieren.

**Empfehlung:** Write-to-temp + `os.rename()` (atomic auf gleinem Filesystem).

---

#### 🟡 MITTEL: Unused Dependency

`pytz==2024.1` ist in `pyproject.toml` als Dependency gelistet, wird aber nirgends importiert (nur `zoneinfo.ZoneInfo` wird verwendet).

---

#### 🟡 MITTEL: Korrupter Dateiname in `/data/`

Die Datei `data/user_67207672070553605536.json` scheint eine fehlerhafte Verkettung zweier Chat-IDs zu sein (672070553 + 6720705536?). Sollte bereinigt werden.

---

#### 🟡 MITTEL: Globaler State statt Dependency Injection

`main_new.py` nutzt globale Variablen (`config`, `repo`, `lernplan_service`, etc.), die via `init_globals()` befüllt werden. Das erschwert Testbarkeit und macht parallele Initialisierung unmöglich.

---

### 2.4 Test-Bewertung

| Test-Datei | Tests | Problem |
|------------|-------|---------|
| `test_config.py` | 7 | ✅ Korrekt, testet neue Config |
| `test_repository.py` | ~7 | ✅ Korrekt, testet neue Repository |
| `test_shared_functionality.py` | 4 | ⚠️ Patcht `bot.main` (Legacy) |
| `test_weekly_overview_improvements.py` | 4 | ⚠️ Patcht `bot.main` (Legacy) |
| `test_time_validation.py` | ? | ⚠️ Patcht `bot.main` (Legacy) |

**~40% der Tests laufen gegen den falschen Code.** Die Tests bestehen ggf. noch, prüfen aber nicht die aktive Codebasis.

---

## 3. Weiterentwicklungskonzept

### 3.1 Vision

> **Vom Erinnerungs-Tool zur Lern-Begleit-Plattform:**
> Der Bot soll nicht nur erinnern, sondern motivieren, Fortschritt sichtbar machen und das Lernen zu einem positiven Erlebnis für Schüler und Eltern entwickeln.

### 3.2 Roadmap

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 0: Stabilisierung          [2 Wochen]    ◀ JETZT
Phase 1: Lern-Tracking & History [3 Wochen]
Phase 2: Gamification & UX       [4 Wochen]
Phase 3: Erweiterte Features     [6 Wochen]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Phase 0: Stabilisierung (Priorität: SOFORT)

> Ziel: Alle kritischen Probleme beheben, technische Schulden abbauen.

| # | Maßnahme | Aufwand | Impact |
|---|----------|---------|--------|
| 0.1 | **Token rotieren** – Neuen Token über BotFather generieren, alten revoken, `bot_config.json` nur Template-Werte commiten | 30 min | 🔴 Kritisch |
| 0.2 | **Legacy `main.py` entfernen** – Archivieren in separatem Branch, aus `src/` entfernen | 1h | 🔴 Hoch |
| 0.3 | **Tests migrieren** – Alle Tests auf `main_new.py` / Service-Layer umschreiben | 4h | 🔴 Hoch |
| 0.4 | **Erinnerungszeiten-Verwaltung** ins Hauptmenü aufnehmen (Add/Del/List) | 3h | 🟠 Hoch |
| 0.5 | **Atomic Writes** für JSON-Persistenz | 1h | 🟡 Mittel |
| 0.6 | **pytz-Dependency entfernen** | 10 min | 🟡 Niedrig |
| 0.7 | **Health-Check verbessern** – Bot-Connectivity prüfen | 1h | 🟡 Mittel |
| 0.8 | **Korrupte Datei** `user_67207672070553605536.json` bereinigen | 10 min | 🟡 Niedrig |

---

### Phase 1: Lern-Tracking & History (UX-Impact: HOCH)

> Ziel: Lernfortschritt sichtbar und nachvollziehbar machen.

#### 1.1 Lernprotokoll (Learning History)

Neues Feld `learning_history` in `UserSettings`:

```python
@dataclass
class LearningEntry:
    date_iso: str           # "2026-02-27"
    weekday: str            # "donnerstag"
    subject: str            # "Mathe"
    planned_minutes: int    # 30
    completed: bool         # True
    learned_response: str   # "yes" | "no"
    comment: str | None     # Optionaler Kommentar
    voice_sent: bool        # Sprachnachricht gesendet?
    timestamp: str          # ISO Timestamp
```

**Vorher:** Daten werden jeden Abend gelöscht → keine History.
**Nachher:** Abgeschlossene Einträge wandern in `learning_history` bevor die Tagesdaten gelöscht werden. Wochen-Statistik funktioniert erstmals mit echten Daten.

#### 1.2 Fortschritts-Dashboard

Neuer Menüpunkt **"📊 Mein Fortschritt"**:

```
📊 DEIN FORTSCHRITT
━━━━━━━━━━━━━━━━━━━━

🔥 Streak: 5 Tage in Folge gelernt!
📅 Diese Woche: 4/5 Tage gelernt
⏱️ Gesamtzeit: 3h 15min

📚 Top-Fächer:
🔢 Mathe      █████████░  2h 10min
🇬🇧 Englisch   ████░░░░░░  1h 05min

📈 Verlauf (letzte 4 Wochen):
KW 8:  ████████░░  4/5 Tage
KW 7:  ██████░░░░  3/5 Tage
KW 6:  ██████████  5/5 Tage
KW 5:  ████░░░░░░  2/5 Tage
```

#### 1.3 Täglicher Abschluss-Report

Statt nur "Hast du gelernt? Ja/Nein" — ein reicherer Abschluss:

```
📋 TAGESABSCHLUSS — Donnerstag, 27.02.
━━━━━━━━━━━━━━━━━━━━

📚 Geplant: Mathe (30 Min)
⏰ Erinnerungen: 09:00, 14:00

Hast du heute gelernt?
[Ja ✅]  [Teilweise 🔶]  [Nein ❌]
```

Bei "Ja" oder "Teilweise" → Nachfrage:
```
Wie lange hast du ungefähr gelernt?
[15 Min] [30 Min] [45 Min] [60+ Min]
```

→ Echte Lernzeiten statt binäres Ja/Nein.

---

### Phase 2: Gamification & UX (UX-Impact: SEHR HOCH)

> Ziel: Intrinsische Motivation durch Spielelemente und ein positives Erlebnis.

#### 2.1 Streak-System

```
🔥 Streak: 12 Tage!
━━━━━━━━━━━━━━━━━━━━

Meilensteine:
✅  3 Tage  → 🏅 Bronze
✅  7 Tage  → 🥈 Silber
✅ 14 Tage  → 🥇 Gold
⬜ 30 Tage  → 💎 Diamant
⬜ 60 Tage  → 👑 Legende
```

- Streak zählt konsekutive Tage mit "Ja" oder "Teilweise"
- Joker unterbricht den Streak nicht
- Bei Streak-Verlust: ermutigendes GIF + "Neustart ist kein Rückschritt!"
- Neue Meilenstein-Erreichung → Feier-Animation an Schüler UND Eltern

#### 2.2 Wochen-Challenges

Wöchentlich rotierende Mini-Herausforderungen:

| Challenge | Beschreibung | Belohnung |
|-----------|-------------|-----------|
| 🎯 "Perfekte Woche" | 5/5 Tage gelernt | +1 Extra-Joker |
| ⏰ "Frühaufsteher" | 3x vor 10:00 gelernt | Spezielles GIF |
| 📚 "Fächermix" | 3 verschiedene Fächer | Achievement-Badge |
| 🗣️ "Kommentator" | 5x Kommentar/Sprachnachricht | Eltern-Benachrichtigung |

#### 2.3 Verbessertes Morgen-Prompt

**Vorher:**
```
Guten Morgen! ☀️ Plan für heute?
[🔢 Mathe] [🇬🇧 Englisch]
[🏖️ Joker (1 übrig)]
```

**Nachher:**
```
☀️ Guten Morgen! Dein Donnerstag:

📋 Wochenplan: Mathe (30 Min)
🔥 Streak: 5 Tage | 🏅 Nächster Meilenstein: 7 Tage

Was planst du heute?
[🔢 Mathe jetzt planen]
[📚 Anderes Fach]
[🏖️ Joker (1 übrig)]

💡 Tipp: Wenn du vor 10 Uhr startest, zählt es für die "Frühaufsteher"-Challenge!
```

#### 2.4 Eltern-Wochenreport

Sonntagabend automatisch an Eltern:

```
📊 WOCHENBERICHT für [Kind]
━━━━━━━━━━━━━━━━━━━━

📅 Gelernt: 4/5 Tage  (Vorwoche: 3/5)  ↑
⏱️ Gesamtzeit: 2h 45min (Vorwoche: 1h 30min)  ↑↑
🔥 Streak: 4 Tage aktiv
🃏 Joker: 0 verwendet

📚 Fächer-Verteilung:
🔢 Mathe: 1h 30min (3x)
🇬🇧 Englisch: 1h 15min (2x)

💬 Kommentare der Woche:
• Mo: "War einfach heute" 
• Mi: 🎤 (Sprachnachricht)

👍 Bewertung: Gute Woche! Steigerung gegenüber Vorwoche.
```

---

### Phase 3: Erweiterte Features (UX-Impact: MITTEL-HOCH)

> Ziel: Vom einzelnen Bot zur umfassenden Lern-Begleitung.

#### 3.1 Prüfungstermine & Countdown

```
📝 NÄCHSTE PRÜFUNGEN
━━━━━━━━━━━━━━━━━━━━

🔢 Mathe-Klassenarbeit
   📅 05.03.2026 (6 Tage)
   💡 Empfehlung: Heute 30 Min Mathe einplanen

🇬🇧 Englisch-Vokabeltest
   📅 12.03.2026 (13 Tage)
```

- Automatische Erinnerung 3 Tage + 1 Tag vor der Prüfung
- Bot schlägt das Fach proaktiv im Morgen-Prompt vor

#### 3.2 Wochenplan-Vorlagen

```
📋 PLAN-VORLAGEN
━━━━━━━━━━━━━━━━

[📐 Mathe-Fokus]      Mo/Mi/Fr Mathe
[🌍 Sprachen-Mix]     Di/Do Englisch, Mi Deutsch
[📚 Ausgewogen]       Täglicher Wechsel
[✏️ Eigene Vorlage erstellen]
```

- Schnell zwischen Vorlagen wechseln (z.B. Klausurwoche vs. normale Woche)
- Eigene Vorlagen speichern und laden

#### 3.3 Multi-Schüler-Support

Erweiterung des 1:1-Modells auf 1:N (ein Elternteil, mehrere Kinder):

```json
{
  "family_group": {
    "parent_chat_id": 672070553,
    "students": [
      {"chat_id": 193788187, "name": "Max", "emoji": "🧑"},
      {"chat_id": 987654321, "name": "Lisa", "emoji": "👧"}
    ]
  }
}
```

Eltern sehen konsolidierte Berichte:
```
📊 FAMILIEN-ÜBERSICHT
━━━━━━━━━━━━━━━━━━━━

🧑 Max: 4/5 Tage | 🔥 Streak: 12
👧 Lisa: 5/5 Tage | 🔥 Streak: 7
```

#### 3.4 Export-Funktion

```
📤 DATEN EXPORTIEREN
━━━━━━━━━━━━━━━━━━━━

[📊 Wochen-Report als PDF]
[📈 Monats-Statistik als CSV]
[📋 Komplette History als JSON]
```

- PDF-Report für Lehrer-Gespräche oder Elternabende
- CSV für eigene Auswertungen

#### 3.5 Intelligente Empfehlungen

Basierend auf dem Lernprotokoll:

```
💡 EMPFEHLUNG
━━━━━━━━━━━━━━━━━━━━

Du hast diese Woche noch kein Englisch gelernt,
aber eine Prüfung in 5 Tagen.

Vorschlag: Heute 30 Min Englisch statt Mathe?
[Ja, Englisch einplanen] [Nein, bei Mathe bleiben]
```

---

### 3.3 Priorisierungs-Matrix

```
                    UX-Impact
              NIEDRIG          HOCH
         ┌──────────────┬──────────────┐
   N  H  │              │ Streak-Sys.  │
   I  O  │              │ Gamification │
   E  C  │              │ Morgen-Promp │
   D  H  │              │ Prüfungen   │
   R     ├──────────────┼──────────────┤
   I  N  │ Multi-User   │ Lern-History │
   G  I  │ Export       │ Fortschrits- │
      E  │ Vorlagen     │  Dashboard   │
      D  │              │ Eltern-Rep.  │
      R  │              │ Erinnerungs- │
      I  │              │  verwaltung  │
      G  └──────────────┴──────────────┘
          HOCH         NIEDRIG
                 Aufwand
```

**Quick Wins** (niedriger Aufwand, hoher Impact):
1. Lern-History einführen (Phase 1.1)
2. Erinnerungszeiten-Verwaltung im Menü (Phase 0.4)
3. Erweitertes Feedback (Ja/Teilweise/Nein + Dauer)
4. Streak-Zähler

**Strategische Investitionen** (höherer Aufwand, hoher Impact):
1. Gamification-System
2. Fortschritts-Dashboard
3. Eltern-Wochenreport
4. Prüfungstermine & Countdown

---

## 4. Technische Empfehlungen für die Umsetzung

### 4.1 Datenmodell-Erweiterung

```python
@dataclass
class UserSettings:
    chat_id: int
    reminder_times: list[str]
    week_plan: dict[str, DayPlan]
    jokers_available: int
    last_joker_reset_iso: str
    daily_dynamic_plan: list[dict]
    
    # NEU — Phase 1
    learning_history: list[LearningEntry]    # Persistente Lern-Historie
    current_streak: int                       # Aktive Serie
    longest_streak: int                       # Rekord
    
    # NEU — Phase 2
    achievements: list[str]                   # Erreichte Badges
    weekly_challenges: dict                   # Aktive Challenges
    
    # NEU — Phase 3
    exams: list[ExamEntry]                    # Prüfungstermine
    plan_templates: dict[str, dict]           # Gespeicherte Vorlagen
```

### 4.2 Datenbank-Migration vorbereiten

Bei wachsender Datenmenge (History, Achievements) wird JSON-Persistenz an Grenzen stoßen. Empfohlener Migrationspfad:

```
JSON (jetzt) → SQLite (Phase 2) → PostgreSQL (optional, Phase 3+)
```

SQLite bietet: Atomare Schreibvorgänge, Queries, Backup-Fähigkeit — ohne externen Service.

### 4.3 Architektur-Empfehlungen

| Bereich | Empfehlung |
|---------|-----------|
| **Dependency Injection** | Globale Variablen durch Application-Context ersetzen (z.B. `context.bot_data`) |
| **Repository Pattern** | `SettingsRepository` um History-spezifische Methoden erweitern |
| **Event-System** | Für Streak-Updates, Achievement-Checks etc. ein einfaches Event-Bus-Pattern |
| **Idempotente Jobs** | Scheduler-Jobs so gestalten, dass Doppelt-Ausführung keinen Schaden anrichtet |

---

## 5. Zusammenfassung

### Was gut läuft
Der LernplanReminderBot v2 hat eine **solide technische Basis** mit sauberer Architektur, guter Docker-Integration und durchdachtem Konfigurationsmanagement. Die Kernidee — geteilte Lernplanung zwischen Schüler und Eltern — ist wertvoll und gut umgesetzt.

### Was dringend behoben werden muss
1. 🔴 **Token-Leak** im Git-Repository
2. 🔴 **Legacy-Code entfernen** und Tests migrieren
3. 🟠 **Lern-History** einführen (Statistiken funktionieren aktuell nicht)
4. 🟠 **Erinnerungszeiten-Verwaltung** im Menü ergänzen

### Größtes UX-Potenzial
Die Einführung von **Streak-System**, **echtem Lernfortschritt** und **Gamification** kann das Nutzererlebnis transformieren: Vom passiven "Wirst du erinnert"-Tool hin zu einem aktiven "Ich will meinen Streak halten"-Erlebnis. Die Forschung zu Habit-Forming (vgl. Nir Eyal, "Hooked") zeigt, dass gerade bei jüngeren Nutzern visuelle Fortschrittsanzeigen und Meilensteine die stärksten Motivatoren sind.

### Empfohlene nächste Schritte
1. **Sofort:** Token rotieren, `bot_config.json` bereinigen
2. **Diese Woche:** Legacy-Code entfernen, Tests migrieren, atomare Writes
3. **Nächste 2 Wochen:** Lern-History + funktionsfähige Statistiken
4. **Nächster Monat:** Streak-System + Gamification-Grundlagen

---

*Dieses Dokument dient als Entscheidungsgrundlage für die strategische Weiterentwicklung des LernplanReminderBot v2. Die Phasen sind so gestaltet, dass jede für sich einen Mehrwert liefert und unabhängig priorisiert werden kann.*
