import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://monitor:monitor@localhost:5432/uptime_monitor",
)

database_url = make_url(DATABASE_URL)
if database_url.drivername in {
    "postgres",
    "postgresql",
    "postgresql+psycopg",
}:
    database_url = database_url.set(drivername="postgresql+asyncpg")

# Translate libpq URL options to asyncpg's connection arguments.
query_options = dict(database_url.query)
query_options.pop("sslmode", None)
query_options.pop("channel_binding", None)
database_url = database_url.set(query=query_options)

connect_args = {"ssl": True} if (database_url.host or "").endswith(".neon.tech") else {}

engine = create_async_engine(
    database_url,
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    connect_args=connect_args,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
