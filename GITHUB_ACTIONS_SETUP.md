# GitHub Actions Setup - GHCR Push Berechtigungen

## Problem

Beim Build erscheint folgender Fehler:
```
ERROR: failed to push ghcr.io/portboy/lernplan-reminder-bot:latest: denied: permission_denied: write_package
```

## Ursache

GitHub Actions benötigt explizite Berechtigung auf Repository-Ebene, um Packages zum GitHub Container Registry (GHCR) zu pushen. Die Workflow-Datei ist bereits korrekt konfiguriert, aber die Repository-Einstellungen müssen angepasst werden.

## Lösung

### Schritt 1: Repository Workflow Permissions ändern

1. Gehe zu deinem Repository auf GitHub: `https://github.com/portboy/LernplanReminderBot_v2`
2. Klicke auf **Settings** (Einstellungen)
3. In der linken Seitenleiste unter "Code and automation" → **Actions** → **General**
4. Scrolle nach unten zu **Workflow permissions**
5. Wähle **"Read and write permissions"** (statt "Read repository contents and packages permissions")
6. ✅ Aktiviere auch **"Allow GitHub Actions to create and approve pull requests"** (optional, aber empfohlen)
7. Klicke auf **Save**

### Schritt 2: Workflow erneut ausführen

Nach dem Ändern der Einstellungen:

1. Gehe zu **Actions** Tab
2. Wähle den fehlgeschlagenen Workflow Run
3. Klicke auf **Re-run all jobs**

Oder trigger den Workflow durch einen neuen Push:
```bash
git commit --allow-empty -m "Trigger workflow after permission fix"
git push
```

## Verifizierung

Der Workflow sollte nun erfolgreich laufen und das Docker Image zu GHCR pushen:
- ✅ Workflow Status: Success
- ✅ Package sichtbar unter: `https://github.com/portboy?tab=packages`
- ✅ Image pullbar via: `docker pull ghcr.io/portboy/lernplan-reminder-bot:latest`

## Technische Details

### Was bereits korrekt konfiguriert ist

Die Workflow-Datei `.github/workflows/docker-publish.yml` hat bereits:

```yaml
permissions:
  contents: read
  packages: write  # ✅ Korrekt konfiguriert
```

Und verwendet die richtige Authentifizierung:

```yaml
- name: Log in to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}  # ✅ Nutzt GITHUB_TOKEN
```

### Warum die Repository-Einstellung wichtig ist

- Der `GITHUB_TOKEN` wird automatisch von GitHub Actions bereitgestellt
- Seine Berechtigungen werden durch Repository-Einstellungen gesteuert
- Standardmäßig hat der Token nur Leserechte
- "Read and write permissions" gewährt dem Token die nötigen Schreibrechte für Packages

## Alternative Lösungen (falls nötig)

Falls du aus Sicherheitsgründen keine "Read and write permissions" für alle Workflows möchtest:

### Option A: Personal Access Token (PAT) verwenden

1. Erstelle einen Personal Access Token mit `write:packages` scope
2. Füge ihn als Repository Secret hinzu (z.B. `GHCR_TOKEN`)
3. Ändere die Workflow-Datei:
```yaml
- name: Log in to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.repository_owner }}
    password: ${{ secrets.GHCR_TOKEN }}  # Statt GITHUB_TOKEN
```

**Hinweis:** Diese Lösung ist komplizierter und erfordert Token-Management. Die Repository-Setting-Lösung ist einfacher und wird empfohlen.

## Weitere Hilfe

Falls das Problem weiterhin besteht:
1. Überprüfe, ob du Admin-Rechte auf dem Repository hast
2. Bei Organisations-Repositories: Überprüfe die Organisation-Level Permissions
3. Prüfe die Workflow Logs für detaillierte Fehlermeldungen

## Referenzen

- [GitHub Actions Permissions](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token)
- [GitHub Container Registry Authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
