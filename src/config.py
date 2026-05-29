import os
from pathlib import Path
from urllib.parse import quote_plus

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parent.parent

env_path = ROOT_DIR / ".env"
if load_dotenv:
    load_dotenv(env_path)
elif env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


MONGODB_URL = _env("mongodb_url", "MONGODB_URL", default="mongodb://localhost:27017")
MONGODB_DATABASE = _env("mongodb_database", "MONGODB_DATABASE", default="political_surveys")
ENVIRONMENT = _env("ambiente", "environment", "ENVIRONMENT", default="TEST")

POSTGRES_URL = _env("postgres_url", "POSTGRES_URL")

if not POSTGRES_URL:
    username = quote_plus(_env("user", "POSTGRES_USER", default="postgres") or "")
    password = _env("password", "postgres_password", "POSTGRES_PASSWORD", "DB_PASSWORD")
    password_part = f":{quote_plus(password)}" if password else ""
    host = _env("host", "POSTGRES_HOST", default="localhost")
    port = _env("port", "POSTGRES_PORT", default="5432")
    database = _env("database", "POSTGRES_DB", default="postgres")
    if "supabase.com" in (host or "") and not password:
        raise RuntimeError(
            "Falta password de Postgres en .env. Para Supabase agrega password=<tu_password> "
            "o usa postgres_url con la URL completa."
        )
    POSTGRES_URL = f"postgresql+psycopg2://{username}{password_part}@{host}:{port}/{database}"
