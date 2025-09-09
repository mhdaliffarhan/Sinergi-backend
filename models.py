from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Time, ForeignKey, Table, Boolean, DATE, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

user_team_link = Table('user_team_link', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('team_id', Integer, ForeignKey('teams.id'), primary_key=True)
)

anggota_aktivitas_link = Table('anggota_aktivitas', Base.metadata,
    Column('aktivitas_id', Integer, ForeignKey('aktivitas.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    nama_tim = Column(String, unique=False, nullable=False)
    valid_from = Column(DATE, nullable=False)
    valid_until = Column(DATE, nullable=False)
    ketua_tim_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ketua_tim = relationship("User", foreign_keys=[ketua_tim_id])
    
    users = relationship("User", secondary=user_team_link, back_populates="teams")
    aktivitas = relationship("Aktivitas", back_populates="team")
    projects = relationship("Project", back_populates="team")
    warna = Column(String(7), nullable=True, default="#3b82f6")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    nama_project = Column(String, index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    project_leader_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    project_leader = relationship("User", back_populates="created_projects")
    team = relationship("Team", back_populates="projects")
    aktivitas = relationship("Aktivitas", back_populates="project")
    dokumen = relationship("Dokumen", back_populates="project")

class Aktivitas(Base):
    __tablename__ = "aktivitas"
    id = Column(Integer, primary_key=True, index=True)
    nama_aktivitas = Column(String, index=True, nullable=False)
    deskripsi = Column(Text, nullable=True)
    tanggal_mulai = Column(DATE, nullable=True)
    tanggal_selesai = Column(DATE, nullable=True)
    jam_mulai = Column(Time, nullable=True)
    jam_selesai = Column(Time, nullable=True)
    dibuat_pada = Column(TIMESTAMP(timezone=True), server_default='now()')
    creator_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    melibatkan_kepala = Column(Boolean, default=False, nullable=False)

    creator = relationship("User", back_populates="created_aktivitas")
    team = relationship("Team", back_populates="aktivitas")
    project = relationship("Project", back_populates="aktivitas")
    dokumen = relationship("Dokumen", back_populates="aktivitas", cascade="all, delete-orphan")
    daftar_dokumen_wajib = relationship("DaftarDokumen", back_populates="aktivitas", cascade="all, delete-orphan")
    users = relationship("User", secondary=anggota_aktivitas_link, back_populates="aktivitas", cascade="all, delete")

class Dokumen(Base):
    __tablename__ = "dokumen"
    id = Column(Integer, primary_key=True, index=True)
    keterangan = Column(Text, nullable=False)
    tipe = Column(String(10), nullable=False)
    path_atau_url = Column(Text, nullable=False)
    nama_file_asli = Column(String, nullable=True)
    tipe_file_mime = Column(String, nullable=True)
    diunggah_pada = Column(DateTime, server_default=func.now())
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="dokumen")
    
    aktivitas_id = Column(Integer, ForeignKey("aktivitas.id"), nullable=True) 
    aktivitas = relationship("Aktivitas", back_populates="dokumen")

class DaftarDokumen(Base):
    __tablename__ = "daftar_dokumen"
    id = Column(Integer, primary_key=True, index=True)
    nama_dokumen = Column(String, nullable=False)
    status_pengecekan = Column(Boolean, default=False, nullable=False)
    dokumen_id = Column(Integer, ForeignKey("dokumen.id"), nullable=True)
    aktivitas_id = Column(Integer, ForeignKey("aktivitas.id"), nullable=False)
    aktivitas = relationship("Aktivitas", back_populates="daftar_dokumen_wajib")
    dokumen_terkait = relationship("Dokumen")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nama_lengkap = Column(String)
    is_active = Column(Boolean, default=False)
    sistem_role_id = Column(Integer, ForeignKey("sistem_roles.id"))
    jabatan_id = Column(Integer, ForeignKey("jabatan.id"))
    foto_profil_url = Column(Text, nullable=True) 
    sistem_role = relationship("SistemRole")
    jabatan = relationship("Jabatan")
    teams = relationship("Team", secondary=user_team_link, back_populates="users")
    created_aktivitas = relationship("Aktivitas", back_populates="creator")
    created_projects = relationship("Project", back_populates="project_leader")
    
    # Gunakan objek Table yang sudah diperbaiki
    aktivitas = relationship("Aktivitas", secondary=anggota_aktivitas_link, back_populates="users")

class SistemRole(Base):
    __tablename__ = "sistem_roles"
    id = Column(Integer, primary_key=True)
    nama_role = Column(String, unique=True, nullable=False)

class Jabatan(Base):
    __tablename__ = "jabatan"
    id = Column(Integer, primary_key=True)
    nama_jabatan = Column(String, unique=True, nullable=False)