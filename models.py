from sqlalchemy import Column, Integer, String, Text, text, TIMESTAMP, Time, ForeignKey, Table, Boolean, DATE, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from database import Base

# --- LINK TABLES ---

user_team_link = Table('user_team_link', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('team_id', Integer, ForeignKey('teams.id'), primary_key=True),
    Column('team_role', String(50), nullable=False, server_default='member')
)

anggota_aktivitas_link = Table('anggota_aktivitas', Base.metadata,
    Column('aktivitas_id', Integer, ForeignKey('aktivitas.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

aktivitas_tim_terkait_link = Table(
    "aktivitas_tim_terkait_link",
    Base.metadata,
    Column("aktivitas_id", Integer, ForeignKey("aktivitas.id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("teams.id"), primary_key=True),
)

# --- MODELS ---

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
    aktivitas_terkait = relationship("Aktivitas", secondary=aktivitas_tim_terkait_link, back_populates="tim_terkait")

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

    public_id = Column(
        UUID(as_uuid=True),
        primary_key = False,
        server_default=text("gen_random_uuid()"),
        nullable=False,
        unique=True,
        index=True
    )

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
    parent_id = Column(Integer, ForeignKey("aktivitas.id"), nullable=True, index=True)
    kalender_view = Column(Boolean, default=True, nullable=False, index=True) 
    status = Column(String(50), default='Belum Selesai', nullable=False, index=True)

    # Relationships
    creator = relationship("User", back_populates="created_aktivitas")
    team = relationship("Team", back_populates="aktivitas")
    project = relationship("Project", back_populates="aktivitas")
    
    dokumen = relationship("Dokumen", back_populates="aktivitas", cascade="all, delete-orphan")
    daftar_dokumen_wajib = relationship("DaftarDokumen", back_populates="aktivitas", cascade="all, delete-orphan")
    users = relationship("User", secondary=anggota_aktivitas_link, back_populates="aktivitas", cascade="all, delete")
    tim_terkait = relationship("Team", secondary=aktivitas_tim_terkait_link, back_populates='aktivitas_terkait')
    reminders = relationship("AktivitasReminder", back_populates="aktivitas", cascade="all, delete-orphan")

    # Self-Referential Relationships (Parent <-> Children)
    parent = relationship("Aktivitas", remote_side=[id], back_populates="children")
    children = relationship("Aktivitas", back_populates="parent", cascade="all, delete-orphan")

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

    daftar_dokumen_id = Column(Integer, ForeignKey("daftar_dokumen.id"), nullable=True)
    checklist_item = relationship("DaftarDokumen", back_populates="files")

class DaftarDokumen(Base):
    __tablename__ = "daftar_dokumen"
    id = Column(Integer, primary_key=True, index=True)
    nama_dokumen = Column(String, nullable=False)
    status_pengecekan = Column(Boolean, default=False, nullable=False)
    aktivitas_id = Column(Integer, ForeignKey("aktivitas.id"), nullable=False)
    aktivitas = relationship("Aktivitas", back_populates="daftar_dokumen_wajib")
    files = relationship("Dokumen", back_populates="checklist_item", cascade="all, delete-orphan")

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
    nip = Column(String(18), nullable= True, unique=True, index=True)
    nipbps = Column(String(9), nullable=True, unique=True, index=True)

    # Info Pangkat/Golongan
    gol_akhir = Column(String(10), nullable=True)
    tmt_gol = Column(DATE, nullable=True) # TMT Golongan

    # Info Jabatan (TMT)
    tmt_jab = Column(DATE, nullable=True) # TMT Jabatan

    # Info Lainnya
    status_kepegawaian = Column(String(50), nullable=True) # Misal: PNS, PPNPN
    jenis_kelamin = Column(String(20), nullable=True) # Misal: Laki-laki, Perempuan

    # Info Kontak (untuk WA)
    nohp = Column(String(20), nullable=True, unique=True, index=True)
    
    # [BARU] Timestamp Last Login
    last_login = Column(DateTime(timezone=True), nullable=True)

    sistem_role = relationship("SistemRole")
    jabatan = relationship("Jabatan")
    teams = relationship("Team", secondary=user_team_link, back_populates="users")
    created_aktivitas = relationship("Aktivitas", back_populates="creator")
    created_projects = relationship("Project", back_populates="project_leader")
    aktivitas = relationship("Aktivitas", secondary=anggota_aktivitas_link, back_populates="users")
    notifikasi = relationship("Notifikasi", back_populates="user") 

class SistemRole(Base):
    __tablename__ = "sistem_roles"
    id = Column(Integer, primary_key=True)
    nama_role = Column(String, unique=True, nullable=False)

class Jabatan(Base):
    __tablename__ = "jabatan"
    id = Column(Integer, primary_key=True)
    nama_jabatan = Column(String, unique=True, nullable=False)

class Notifikasi(Base):
    __tablename__ = "notifikasi"
    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    related_activity_id = Column(Integer, ForeignKey("aktivitas.id", ondelete="CASCADE"), nullable=True)
    related_project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    title = Column(String(255), nullable=False)
    massage = Column(Text, nullable=True)
    link_to = Column(String, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifikasi")

class AktivitasReminder(Base):
    __tablename__ = "aktivitas_reminders"

    id = Column(Integer, primary_key=True, index=True)
    aktivitas_id = Column(Integer, ForeignKey("aktivitas.id", ondelete="CASCADE"), nullable=False)
    reminder_type = Column(String(20), nullable=False) # 'manual', 'hari_h', 'h_minus_2'
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="pending", index=True) # 'pending', 'sent', 'failed', 'cancelled'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    aktivitas = relationship("Aktivitas", back_populates="reminders")

class WaQueue(Base):
    __tablename__ = "wa_queue"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="pending", index=True) # 'pending', 'sent', 'failed', 'cancelled'
    scheduled_at = Column(DateTime(timezone=True), nullable=True) # Audit: kapan seharusnya dikirim
    aktivitas_id = Column(Integer, ForeignKey("aktivitas.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)