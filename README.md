# **🎓 Lernplan Reminder Bot (v2) – Der Autonomie-Coach**

**Schluss mit dem täglichen Eltern-Kind-Streit ums Lernen.**

Dieser Telegram-Bot ist mehr als nur ein Wecker. Er ist ein digitaler Assistent, der Schülern hilft, ihren Tag selbstständig zu planen, und Eltern informiert hält, ohne dass sie "nerven" müssen.

## **🌟 Warum dieser Bot?**

Viele Eltern kennen das Problem: Man erinnert das Kind ans Vokabellernen, das Kind fühlt sich kontrolliert, die Stimmung kippt.

**Das Konzept dieses Bots ("The Autonomy Coach"):**

Statt starrer Befehle ("Lerne jetzt\!") setzt dieser Bot auf **Selbstbestimmung**.

1. **Das Kind entscheidet morgens selbst**, *wann* es lernen möchte.  
2. **Der Bot ist der neutrale Assistent**, der an die *eigene* Zusage erinnert.  
3. **Gamification (Joker-System)** sorgt für Motivation und erlaubt legitime Pausen.  
4. **Eltern werden passiv informiert** (durch weitergeleitete Sprachnachrichten), statt aktiv kontrollieren zu müssen.

## **🔄 Der Tagesablauf (The Core Loop)**

So fühlt sich die Nutzung für dein Kind an:

### **1️⃣ 07:30 Uhr – Der "Morning Prompt"**

Der Bot weckt nicht mit Aufgaben, sondern fragt: *"Guten Morgen\! ☀️ Wie sieht dein Plan heute aus?"*

* Das Kind sieht die Fächer (z. B. Mathe, Englisch).  
* **Action:** Das Kind wählt ein Fach und tippt auf eine Uhrzeit (z. B. 15:00 Uhr).  
* **Oder:** Das Kind zieht einen **Joker** 🏖️ (1x pro Woche) und hat heute frei.

### **2️⃣ Der gewählte Zeitpunkt – Die Umsetzung**

Zur gewählten Zeit (z. B. 15:00 Uhr) meldet sich der Bot: *"🔔 Zeit für Mathe, wie besprochen\!"*

* Das Kind lernt.  
* **Action:** Statt langweiliger Checkboxen schickt das Kind einfach eine **Sprachnachricht** an den Bot: *"Habe 20 Minuten Brüche geübt."*  
* **Feature:** Der Bot leitet diese Nachricht **sofort an die Eltern weiter**. Papa/Mama wissen Bescheid, ohne nachgefragt zu haben.

### **3️⃣ 20:00 Uhr – Der Check-in**

Der Tagesabschluss. *"Hast du heute alles geschafft?"*

* **Action:** Ja ✅ / Nein ❌.  
* **Belohnung:** Bei Erfolg gibt es ein motivierendes Bild (z. B. Pferde, Katzen, Memes).  
* **Kein Druck:** Bei "Nein" gibt es kein Schimpfen, sondern ein aufmunterndes GIF.

## **✨ Features im Überblick**

### **👶 Für das Kind (Student)**

* **Volle Kontrolle:** "Ich bestimme, wann ich lerne."  
* **Joker-System:** Einmal pro Woche "frei" machen dürfen (wird Montags automatisch aufgefüllt).  
* **Voice-First:** Erledigungen einfach per Sprachnachricht melden.  
* **Kein Spam:** Der Bot nervt nicht, wenn man den Joker nutzt.

### **👨‍👩‍👧 Für die Eltern (Parent)**

* **Entspannung:** Du musst nicht mehr drängeln. Der Bot übernimmt die Struktur.  
* **Transparenz:** Du bekommst die Sprachnachrichten ("Habe Vokabeln gelernt") direkt weitergeleitet.  
* **Tagesreport:** Um 20:00 Uhr erhältst du eine Zusammenfassung: Was war geplant? Was wurde erledigt?  
* **Admin-Menü:** Über einen eigenen Menü-Button kannst du den groben Wochenplan ("Montags ist eigentlich Mathe") vordefinieren.

## **🛠️ Technische Installation & Deployment**

Der Bot ist als **Docker-Container** konzipiert und läuft perfekt auf einem Home-Server (z. B. Unraid, Raspberry Pi, Synology).

### **Voraussetzungen**

1. Ein **Telegram Bot Token** (von [@BotFather](https://t.me/BotFather)).  
2. Zwei Telegram-Accounts (Kind & Elternteil).  
3. Docker & Docker Compose.

### **Option A: Schnellstart (Docker Compose)**

Erstelle eine Datei docker-compose.yml und eine .env Datei im selben Ordner.

**.env Datei:**

TELEGRAM\_TOKEN=dein\_token\_hier  
STUDENT\_CHAT\_ID=123456789  
PARENT\_CHAT\_ID=987654321  
TIMEZONE=Europe/Berlin  
DATA\_DIR=data  
LOG\_LEVEL=INFO

**docker-compose.yml:**

version: "3.9"  
services:  
  lernplan-bot:  
    image: ghcr.io/portboy/lernplan-reminder-bot-v2:latest  
    container\_name: lernplan-bot  
    restart: unless-stopped  
    env\_file: .env  
    volumes:  
      \- ./data:/app/data

Starten:

docker compose up \-d

### **Option B: Unraid Server (Detailliert)**

Der Bot speichert seinen Status (Joker, Pläne) in JSON-Dateien. Diese müssen persistent sein.

1. **Verzeichnisse erstellen:**  
   Öffne das Unraid Terminal:  
   mkdir \-p /mnt/user/appdata/LernplanReminderBot/data

2. **Konfiguration anlegen:**  
   Erstelle die Datei /mnt/user/appdata/LernplanReminderBot/.env (siehe oben für Inhalt).  
3. **Container starten (per Terminal oder Docker Compose Plugin):**  
   Wenn du das "Docker Compose Manager" Plugin nutzt, kopiere den Inhalt von Option A dort hinein.  
   Pfade anpassen:  
   * Host Pfad: /mnt/user/appdata/LernplanReminderBot/data  
   * Container Pfad: /app/data

## **⚙️ Konfiguration & IDs herausfinden**

### **1\. Chat IDs ermitteln**

Damit der Bot weiß, wer Kind und wer Elternteil ist:

1. Sende mit dem Handy des **Kindes** /start an den Bot.  
2. Sende mit dem Handy des **Elternteils** /start an den Bot.  
3. Schau in die Logs:  
   docker logs lernplan-bot

   Dort siehst du Einträge wie User 123456789 started bot.  
4. Trage diese IDs in deine .env Datei ein und starte den Container neu (docker compose restart).

### **2\. Environment Variablen (Referenz)**

| Variable | Pflicht? | Beschreibung |
| :---- | :---- | :---- |
| TELEGRAM\_TOKEN | ✅ Ja | Der API Token vom BotFather. |
| STUDENT\_CHAT\_ID | ✅ Ja | ID des Kindes. Ohne diese ID funktioniert der Bot nicht korrekt (kein Check-in). |
| PARENT\_CHAT\_ID | ❌ Nein | ID der Eltern. Wenn gesetzt, werden Sprachnachrichten und Reports hierhin gesendet. |
| DATA\_DIR | ❌ Nein | Ordner für JSON-Daten (Default: data). |
| LOG\_LEVEL | ❌ Nein | INFO (Standard) oder DEBUG für Fehlersuche. |

## **🐛 Troubleshooting & FAQ**

### **Häufige Probleme**

| Symptom | Ursache | Lösung |
| :---- | :---- | :---- |
| **Bot antwortet gar nicht** | Falscher Token oder Container läuft nicht. | Prüfe docker logs lernplan-bot auf Fehler. Prüfe Token in .env. |
| **20-Uhr Frage fehlt** | STUDENT\_CHAT\_ID falsch oder nicht gesetzt. | ID in .env prüfen. Bot muss *vor* 20:00 Uhr laufen. |
| **Keine Eltern-Info** | PARENT\_CHAT\_ID nicht gesetzt. | In .env ergänzen und neu starten. |
| **Daten (Joker) weg nach Neustart** | Volume nicht korrekt gemountet. | Prüfe in docker-compose.yml, ob ./data:/app/data korrekt ist. |
| **"Zeiten verwalten" Menü noch da** | Alte Version läuft noch. | Führe docker compose pull aus, um das Update zu laden. |

### **Updates einspielen**

Um die neueste Version zu erhalten (z. B. Bugfixes):

**Manuell:**

docker compose pull  
docker compose up \-d

**Automatisch (Watchtower):**

Wenn du Watchtower auf deinem Unraid/Server nutzt, wird der Bot automatisch aktualisiert, sobald ein neues Image auf GitHub verfügbar ist.

### **Backup**

Alle Daten liegen im data/ Ordner als .json Dateien.

* **Backup:** Kopiere einfach den Ordner /mnt/user/appdata/LernplanReminderBot/data.  
* **Restore:** Kopiere die Dateien zurück und starte den Container neu.

## **🤖 Tech Stack**

* **Sprache:** Python 3.11+  
* **Framework:** python-telegram-bot (Async)  
* **Scheduling:** APScheduler (für dynamische Jobs und Cron-Logik)  
* **Datenbank:** Einfache JSON-Files (keine externe DB nötig, leicht zu sichern)  
* **Container:** Docker (Multi-Arch: amd64/arm64)

## **📄 Lizenz**

MIT License \- Fühlt euch frei, den Bot für eure Familie anzupassen\!
