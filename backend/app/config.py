import os

# Async SQLAlchemy URL. SQLite for local dev, Postgres (asyncpg) in production.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/todo.db")

# ntfy push notifications. Reminders are disabled until NTFY_TOPIC is set.
# The topic is effectively a password: anyone who knows it can read/write it
# on a public server, so use a long random string (e.g. `openssl rand -hex 12`).
NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_TOKEN = os.environ.get("NTFY_TOKEN", "")

# IANA timezone used to decide "today" and quiet hours for reminders.
TIMEZONE = os.environ.get("TIMEZONE", "America/New_York")

# Reminders are only sent inside this local-time window (24h clock), so a
# task crossing its reminder threshold at midnight pings you at breakfast.
NOTIFY_FROM_HOUR = int(os.environ.get("NOTIFY_FROM_HOUR", "8"))
NOTIFY_UNTIL_HOUR = int(os.environ.get("NOTIFY_UNTIL_HOUR", "21"))

# How often the reminder loop wakes up.
REMINDER_CHECK_SECONDS = int(os.environ.get("REMINDER_CHECK_SECONDS", "300"))

# Optional absolute URL of the web app; tapping a notification opens the task.
APP_URL = os.environ.get("APP_URL", "").rstrip("/")
