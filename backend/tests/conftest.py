import os


# Application modules construct Settings during import. Unit tests use inert
# connection strings and replace database access before any connection occurs.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/ecotraffic_test",
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://test:test@localhost:5432/ecotraffic_test",
)
os.environ.setdefault("DATABASE_NAME", "ecotraffic_test")
os.environ.setdefault("DATABASE_USER", "test")
os.environ.setdefault("DATABASE_PASSWORD", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
