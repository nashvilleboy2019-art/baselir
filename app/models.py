from sqlalchemy import Column, Integer, String, DateTime, Text, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="auditeur")
    nom = Column(String(100), nullable=True)
    prenom = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AppConfig(Base):
    __tablename__ = "app_config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)


# --- Référentiels fixes ---

class RefStatut(Base):
    __tablename__ = "ref_statuts"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False, unique=True)
    color = Column(String(30), nullable=False, default="gray")
    ordre = Column(Integer, default=0)


class RefFiliale(Base):
    __tablename__ = "ref_filiales"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False, unique=True)
    ordre = Column(Integer, default=0)


class RefDescription(Base):
    __tablename__ = "ref_descriptions"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(200), nullable=False, unique=True)
    ordre = Column(Integer, default=0)


class RefService(Base):
    __tablename__ = "ref_services"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False, unique=True)
    ordre = Column(Integer, default=0)


class RefSociete(Base):
    __tablename__ = "ref_societes"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False, unique=True)
    ordre = Column(Integer, default=0)


class RefRole(Base):
    __tablename__ = "ref_roles"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False, unique=True)
    ordre = Column(Integer, default=0)


class RefDomaine(Base):
    __tablename__ = "ref_domaines"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False, unique=True)
    ordre = Column(Integer, default=0)


# --- Référentiels dynamiques (champs personnalisés) ---

class RefCustomType(Base):
    __tablename__ = "ref_custom_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)   # slug ex: "region"
    label = Column(String(100), nullable=False)               # libellé ex: "Région"
    ordre = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    values = relationship("RefCustomValue", back_populates="custom_type",
                          cascade="all, delete-orphan", order_by="RefCustomValue.ordre")


class RefCustomValue(Base):
    __tablename__ = "ref_custom_values"
    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, ForeignKey("ref_custom_types.id"), nullable=False)
    label = Column(String(200), nullable=False)
    ordre = Column(Integer, default=0)
    custom_type = relationship("RefCustomType", back_populates="values")


class HabilitationCustomField(Base):
    __tablename__ = "habilitation_custom_fields"
    id = Column(Integer, primary_key=True, index=True)
    habilitation_id = Column(Integer, ForeignKey("habilitations.id"), nullable=False)
    custom_type_id = Column(Integer, ForeignKey("ref_custom_types.id"), nullable=False)
    custom_value_id = Column(Integer, ForeignKey("ref_custom_values.id"), nullable=True)
    custom_type = relationship("RefCustomType")
    custom_value = relationship("RefCustomValue")


# --- Habilitations ---

class Habilitation(Base):
    __tablename__ = "habilitations"
    id = Column(Integer, primary_key=True, index=True)
    nom_prenom = Column(String(200), nullable=False, index=True)

    statut_id = Column(Integer, ForeignKey("ref_statuts.id"), nullable=True)
    filiale_id = Column(Integer, ForeignKey("ref_filiales.id"), nullable=True)
    description_id = Column(Integer, ForeignKey("ref_descriptions.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("ref_services.id"), nullable=True)
    societe_id = Column(Integer, ForeignKey("ref_societes.id"), nullable=True)
    role_id = Column(Integer, ForeignKey("ref_roles.id"), nullable=True)
    domaine_id = Column(Integer, ForeignKey("ref_domaines.id"), nullable=True)

    date_octroi = Column(Date, nullable=True)
    date_attestation = Column(Date, nullable=True)
    attestation_filename = Column(String(255), nullable=True)
    date_sensibilisation = Column(Date, nullable=True)
    sensibilisation_filename = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    statut = relationship("RefStatut", foreign_keys=[statut_id])
    filiale = relationship("RefFiliale", foreign_keys=[filiale_id])
    description = relationship("RefDescription", foreign_keys=[description_id])
    service = relationship("RefService", foreign_keys=[service_id])
    societe = relationship("RefSociete", foreign_keys=[societe_id])
    role = relationship("RefRole", foreign_keys=[role_id])
    domaine = relationship("RefDomaine", foreign_keys=[domaine_id])
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

    history = relationship("HabilitationHistory", back_populates="habilitation",
                           order_by="HabilitationHistory.changed_at.desc()")
    custom_fields = relationship("HabilitationCustomField",
                                 primaryjoin="Habilitation.id == HabilitationCustomField.habilitation_id",
                                 cascade="all, delete-orphan")


class HabilitationHistory(Base):
    __tablename__ = "habilitations_history"
    id = Column(Integer, primary_key=True, index=True)
    habilitation_id = Column(Integer, ForeignKey("habilitations.id"), nullable=False)
    action = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    note = Column(String(500), nullable=True)

    habilitation = relationship("Habilitation", back_populates="history")
    user = relationship("User", foreign_keys=[changed_by])


class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True)
    key_prefix = Column(String(12), nullable=False)
    active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    creator = relationship("User", foreign_keys=[created_by])


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    resource = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
