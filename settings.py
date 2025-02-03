from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "main/static"]

ALLOWED_HOSTS = [
    "re-rmi.onrender.com",
    "localhost",
    "127.0.0.1",
]

TEMPLATES = [
    {
        # ...existing code...
        'DIRS': [BASE_DIR / "main/templates/main"],
        # ...existing code...
        # ...existing code...
    },
]
# ...existing code...
