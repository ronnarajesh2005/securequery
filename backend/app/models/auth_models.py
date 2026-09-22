import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class Researcher(Base):
    __tablename__ = "researchers"

    researcher_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False, default="researcher")
    hospital_scope = Column(String(50), nullable=True, default=None)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())


class ConsentPurpose(Base):
    __tablename__ = "consent_purposes"

    purpose_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purpose_code = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=False)


class ResearcherPermission(Base):
    __tablename__ = "researcher_permissions"

    permission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    researcher_id = Column(UUID(as_uuid=True), ForeignKey("researchers.researcher_id"), nullable=False)
    purpose_id = Column(UUID(as_uuid=True), ForeignKey("consent_purposes.purpose_id"), nullable=False)
    hospital_scope = Column(String(50), nullable=False, default="all")
    data_localization_ok = Column(Boolean, nullable=False, default=True)
    granted_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    entry_id = Column(BigInteger, primary_key=True, autoincrement=True)
    researcher_id = Column(UUID(as_uuid=True), nullable=False)
    query_text = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    dpdp_check_result = Column(String(50), nullable=True)
    risk_check_result = Column(String(50), nullable=True)
    disclosed = Column(Boolean, nullable=True)
    entry_data = Column(Text, nullable=False)
    entry_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=True)
    created_at = Column(String, server_default=func.now())