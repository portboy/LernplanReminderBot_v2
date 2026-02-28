"""Health check script — verifies bot can reach Telegram API."""

import sys


def check() -> bool:
    try:
        import json
        from pathlib import Path

        # 1. Verify config is loadable
        config_paths = [
            Path("userconfig/bot_config.json"),
            Path("/app/userconfig/bot_config.json"),
        ]
        config_ok = False
        for p in config_paths:
            if p.exists():
                with p.open() as f:
                    json.load(f)
                config_ok = True
                break

        if not config_ok:
            print("HEALTH: No config file found")
            return False

        # 2. Verify data directory is writable
        data_paths = [Path("/app/data"), Path("data")]
        data_ok = False
        for d in data_paths:
            if d.is_dir():
                test_file = d / ".health_check"
                try:
                    test_file.write_text("ok")
                    test_file.unlink()
                    data_ok = True
                    break
                except OSError:
                    continue

        if not data_ok:
            print("HEALTH: Data directory not writable")
            return False

        # 3. Verify Telegram API reachable
        import urllib.request

        req = urllib.request.Request("https://api.telegram.org", method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status >= 500:
                print(f"HEALTH: Telegram API returned {resp.status}")
                return False

        return True

    except Exception as e:
        print(f"HEALTH: {e}")
        return False


if __name__ == "__main__":
    sys.exit(0 if check() else 1)
