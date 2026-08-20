import os
from pathlib import Path

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Resolve relative to the backend package (not the process's cwd) so the
# database lands in the same place regardless of where uvicorn/alembic is
# launched from. Override with DATABASE_URL for Postgres/MySQL/etc.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{_BACKEND_ROOT / 'organization.db'}"
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Every Alembic migration in this repo names its foreign keys explicitly
# via batch_op.create_foreign_key('fk_<table>_<column>_<referred_table>',
# ...) so that downgrades can drop_constraint() them by name in SQLite
# batch mode. But plain `Column(ForeignKey(...))` on the models has no
# opinion on constraint naming, so a schema built via Base.metadata.
# create_all() (the documented dev/test workflow: stash -> stamp head ->
# pop -> autogenerate) gets SQLite's anonymous FK names instead -- which
# then makes every migration's downgrade fail with "No such constraint"
# against a create_all()-built database, even though upgrade/downgrade
# both work fine against a database built by actually running the
# migrations in order. This naming_convention makes create_all() agree
# with what the migrations already assume, so downgrade is reliable
# regardless of how the schema was originally built.
NAMING_CONVENTION = {
    # SQLAlchemy's own default -- must be restated explicitly because
    # passing *any* naming_convention dict replaces the whole thing
    # rather than merging with the default, and every indexed column in
    # this codebase (Column(..., index=True)) relies on this pattern to
    # get a name at all.
    "ix": "ix_%(column_0_label)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)
Base = declarative_base(metadata=metadata)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()