from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

Base = declarative_base()

engine_auth = create_engine(settings.auth_db_url)
SessionAuth = sessionmaker(bind=engine_auth, autocommit=False, autoflush=False)


def get_auth_db():
    db = SessionAuth()
    try:
        yield db
    finally:
        db.close()
engine_audit = create_engine(settings.audit_db_url)
SessionAudit = sessionmaker(bind=engine_audit, autocommit=False, autoflush=False)


def get_audit_db():
    db = SessionAudit()
    try:
        yield db
    finally:
        db.close()