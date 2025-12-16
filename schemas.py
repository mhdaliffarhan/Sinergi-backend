from __future__ import annotations
from uuid import UUID
import re
from pydantic import BaseModel, model_validator, field_validator, Field, ConfigDict
from typing import Optional, Any, List
from datetime import date, time, datetime


# Fungsi untuk konversi nama ke camelCase
def to_camel(snake_str: str) -> str:
    parts = snake_str.split('_')
    return parts[0] + "".join(word.capitalize() for word in parts[1:])

def validate_phone_number(nohp: Optional[str]) -> Optional[str]:
    """Helper untuk membersihkan dan memvalidasi nomor HP."""
    if not nohp:
        return None

    # 1. Hapus semua karakter non-numerik (spasi, -, +)
    nohp_numeric = "".join(filter(str.isdigit, nohp.strip()))

    # 2. Jika diawali 08, ganti ke 628
    if nohp_numeric.startswith('08'):
        nohp_numeric = '62' + nohp_numeric[1:]

    # 3. Cek Aturan: Harus '62' dan 11-14 digit total (Sesuai revisi terakhir)
    if not re.match(r"^62\d{9,12}$", nohp_numeric):
         raise ValueError(
            "Nomor HP harus diawali 62 dan memiliki 11-14 digit (misal: 62812...)"
         )

    return nohp_numeric

# Model dasar yang akan melakukan konversi otomatis untuk SEMUA skema
class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )


# ===================================================================
# 1. SKEMA DASAR (Leaf Nodes)
# ===================================================================
class Jabatan(CamelModel):
    id: int
    nama_jabatan: str

class SistemRole(CamelModel):
    id: int
    nama_role: str


# ===================================================================
# 2. SKEMA DOKUMEN (Harus di awal karena dipakai banyak entitas)
# ===================================================================
class DokumenBase(CamelModel):
    keterangan: str
    tipe: str
    path_atau_url: Optional[str] = None
    nama_file_asli: Optional[str] = None
    tipe_file_mime: Optional[str] = None
    checklist_item_id: Optional[int] = None # Untuk payload upload

class DokumenCreate(DokumenBase):
    pass

class Dokumen(DokumenBase):
    id: int
    diunggah_pada: datetime
    aktivitas_id: Optional[int] = None
    project_id: Optional[int] = None
    daftar_dokumen_id: Optional[int] = None # Relasi ke Checklist Item

# ===================================================================
# 3. SKEMA CHECKLIST (DAFTAR DOKUMEN)
# ===================================================================
class DaftarDokumen(CamelModel):
    id: int
    nama_dokumen: str
    status_pengecekan: bool
    # One-to-Many: Satu item checklist punya banyak file
    files: List[Dokumen] = []

class StatusPengecekanUpdate(CamelModel):
    status_pengecekan: bool


# ===================================================================
# 4. SKEMA USER (Partial/Embedded)
# ===================================================================
class UserInTeam(CamelModel):
    id: int
    username: str
    nama_lengkap: Optional[str] = None
    foto_profil_url: Optional[str] = None
    jabatan: Optional[Jabatan] = None

class UserInTeamWithRole(UserInTeam):
    peran: str

class UserInProject(CamelModel):
    id: int
    username: str
    nama_lengkap: Optional[str] = None
    foto_profil_url: Optional[str] = None # Tambahkan foto profil agar tampil di card

class UserInAktivitas(CamelModel):
    id: int
    username: str
    nama_lengkap: Optional[str] = None
    foto_profil_url: Optional[str] = None
    jabatan: Optional[Jabatan] = None # Perbaikan tipe data jabatan

# ===================================================================
# 5. SKEMA TEAM & PROJECT (Partial/Embedded)
# ===================================================================
class TeamInUser(CamelModel):
    id: int
    nama_tim: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None

class TeamInUserWithRole(TeamInUser):
    peran: str

class TeamInProject(CamelModel):
    id: int
    nama_tim: str
    ketua_tim_id: Optional[int] = None
    warna: Optional[str] = None
    ketua_tim: Optional[UserInTeam] = None

class ProjectInUser(CamelModel):
    id: int
    nama_project: str
    project_leader_id: Optional[int] = None
    project_leader: Optional[UserInTeam] = None

# ===================================================================
# 6. SKEMA USER (Full & Create)
# ===================================================================
class UserBase(CamelModel):
    username: str
    nama_lengkap: Optional[str] = None
    foto_profil_url: Optional[str] = None
    nip: Optional[str] = None
    nipbps: Optional[str] = None
    gol_akhir: Optional[str] = None
    tmt_gol: Optional[date] = None
    tmt_jab: Optional[date] = None
    status_kepegawaian: Optional[str] = None
    jenis_kelamin: Optional[str] = None
    nohp: Optional[str] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator('nip')
    @classmethod
    def validate_nip(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        nip_numeric = "".join(filter(str.isdigit, v))
        if len(nip_numeric) != 18:
            raise ValueError("NIP harus 18 digit angka.")
        return nip_numeric

    @field_validator('nipbps')
    @classmethod
    def validate_nipbps(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        nip_numeric = "".join(filter(str.isdigit, v))
        if len(nip_numeric) != 9: 
            raise ValueError("NIP BPS harus 9 digit angka.")
        return nip_numeric 

    @field_validator('nohp')
    @classmethod
    def validate_nohp(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v)

class UserCreate(UserBase):
    password: str
    sistem_role_id: int
    jabatan_id: int

    @model_validator(mode="after")
    def validate_password_strength(self):
        password = self.password
        if len(password) < 8:
            raise ValueError("Password harus minimal 8 karakter")
        if not any(c.isalpha() for c in password):
            raise ValueError("Password harus mengandung huruf")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password harus mengandung angka")
        return self

class AktivitasInUser(CamelModel):
    id: int
    nama_aktivitas: str
    tanggal_mulai: Optional[date] = None
    tanggal_selesai: Optional[date] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None
    # Tambahan agar di profil terlihat statusnya
    status: str = 'Belum Selesai' 

class User(UserBase):
    id: int
    is_active: bool
    sistem_role: SistemRole
    jabatan: Optional[Jabatan] = None
    teams: List[TeamInUserWithRole] = []
    created_projects: List[ProjectInUser] = []
    aktivitas: List[AktivitasInUser] = [] 

class UserWithTeams(UserBase):
    id: int
    is_active: bool
    sistem_role: SistemRole
    jabatan: Optional[Jabatan] = None
    teams: List[TeamInUserWithRole] = []
    is_ketua_tim: bool = False
    ketua_tim_aktif: List[TeamInUser] = []
    created_projects: List[ProjectInUser] = []
    aktivitas: List[AktivitasInUser] = [] 
    last_login: Optional[datetime] = None

class UserUpdate(UserBase):
    nama_lengkap: Optional[str] = None
    sistem_role_id: Optional[int] = None
    jabatan_id: Optional[int] = None
    is_active: Optional[bool] = None

class PasswordUpdate(CamelModel):
    old_password: str
    new_password: str

    @model_validator(mode="after")
    def validate_password_change(self):
        if self.old_password == self.new_password:
            raise ValueError("Password baru tidak boleh sama dengan password lama")
        if len(self.new_password) < 8:
            raise ValueError("Password baru harus minimal 8 karakter")
        if not any(c.isalpha() for c in self.new_password):
            raise ValueError("Password baru harus mengandung huruf")
        if not any(c.isdigit() for c in self.new_password):
            raise ValueError("Password baru harus mengandung angka")
        return self

class UserPage(CamelModel):
    total: int
    items: List[User]

class ProfileUpdate(CamelModel):
    nama_lengkap: Optional[str] = None
    nohp: Optional[str] = None

    @field_validator('nohp')
    @classmethod
    def validate_nohp_profile(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v)

class ForgotPasswordRequest(CamelModel):
    username: str

class ResetPasswordRequest(CamelModel):
    token: str
    new_password: str

# ===================================================================
# 7. SKEMA AKTIVITAS
# ===================================================================
class AktivitasBase(CamelModel):
    nama_aktivitas: str
    deskripsi: Optional[str] = None
    use_date_range: Optional[bool] = False
    use_time: Optional[bool] = False
    tanggal_mulai: Optional[date] = None
    tanggal_selesai: Optional[date] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None
    team_id: Optional[int] = None
    creator_user_id: Optional[int] = None
    project_id: Optional[int] = None
    melibatkan_kepala: Optional[bool] = None
    id_tim_terkait: List[int] = []
    
    # --- FITUR BARU ---
    status: str = 'Belum Selesai'
    parent_id: Optional[int] = None
    kalender_view: bool = True

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ['Belum Selesai', 'Dalam Proses', 'Selesai']
        if v and v not in valid_statuses:
            raise ValueError(f"Status harus salah satu dari: {', '.join(valid_statuses)}")
        return v

class AktivitasCreate(AktivitasBase):
    daftar_dokumen_wajib: List[str] = []
    anggota_aktivitas_ids: List[int] = []
    send_whatsapp: bool = True

    @model_validator(mode='before')
    @classmethod
    def check_required_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            use_date_range = data.get('useDateRange')
            if not use_date_range:
                if not data.get('tanggalMulai'):
                    raise ValueError('Tanggal Pelaksanaan wajib diisi.')
            elif use_date_range:
                if not data.get('tanggalMulai') or not data.get('tanggalSelesai'):
                    raise ValueError('Tanggal Mulai dan Tanggal Selesai wajib diisi.')
        return data

class AktivitasUpdate(AktivitasBase):
    # Optional semua field untuk PATCH/PUT partial
    nama_aktivitas: Optional[str] = None
    status: Optional[str] = None
    kalender_view: Optional[bool] = None
    parent_id: Optional[int] = None

class AktivitasInTeam(CamelModel):
    id: int
    nama_aktivitas: str
    deskripsi: Optional[str] = None
    tanggal_mulai: Optional[date] = None
    tanggal_selesai: Optional[date] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None
    melibatkan_kepala: bool
    status: str
    users: List[UserInAktivitas] = []

# Skema Ringan untuk Dropdown Parent (Efisiensi)
class AktivitasOption(CamelModel):
    id: int
    nama_aktivitas: str

# Skema Aktivitas Anak (Nested)
class AktivitasChild(CamelModel):
    id: int
    nama_aktivitas: str
    tanggal_mulai: Optional[date] = None
    status: str = 'Belum Selesai'

# Skema Aktivitas Induk (Parent Info)
class AktivitasParent(CamelModel):
    id: int
    nama_aktivitas: str

# Skema Aktivitas yang digunakan di dalam Project Detail
# PENTING: Harus menyertakan dokumen agar tidak hilang di detail project
class ProjectAktivitas(CamelModel):
    id: int
    nama_aktivitas: str
    tanggal_mulai: Optional[date] = None
    tanggal_selesai: Optional[date] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None
    deskripsi: Optional[str] = None
    status: str = 'Belum Selesai' # Tambahan
    
    daftar_dokumen_wajib: List[DaftarDokumen] = []
    dokumen: List[Dokumen] = [] # <--- INI PERBAIKAN PENTING
    users: List[UserInAktivitas] = []

# ===================================================================
# 8. SKEMA TEAM (Full)
# ===================================================================
class TeamBase(CamelModel):
    id: int
    nama_tim: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    ketua_tim_id: Optional[int] = None
    warna: Optional[str] = None

class ProjectInTeam(CamelModel):
    id: int
    nama_project: str
    project_leader: Optional[UserInProject] = None
    aktivitas: List[AktivitasInTeam] = []

class TeamDetail(TeamBase):
    projects: List[ProjectInTeam] = []
    aktivitas: List[AktivitasInTeam] = []
    users: List[UserInTeamWithRole] = []
    ketua_tim: Optional[UserInTeam]

class TeamCreate(CamelModel):
    nama_tim: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    ketua_tim_id: Optional[int] = None
    warna: Optional[str] = None
    operator_ids: list[int] = []

class TeamUpdate(CamelModel):
    nama_tim: Optional[str] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    ketua_tim_id: Optional[int] = None
    warna: Optional[str] = None
    operator_ids: Optional[list[int]] = None

class Team(TeamBase):
    id: int
    ketua_tim: Optional[UserInTeam] = None
    users: List[UserInTeam] = []

class TeamPage(CamelModel):
    total: int
    items: List[Team]

# ===================================================================
# 9. SKEMA PROJECT (Full)
# ===================================================================
class ProjectBase(CamelModel):
    nama_project: str
    team_id: Optional[int] = None
    project_leader_id: int

class ProjectCreate(ProjectBase):
    send_whatsapp: bool = True

class ProjectUpdate(CamelModel):
    nama_project: Optional[str] = None
    team_id: Optional[int] = None
    project_leader_id: Optional[int] = None

class Project(ProjectBase):
    id: int
    project_leader: Optional[UserInProject] = None
    team: Optional[TeamInProject] = None
    dokumen: List[Dokumen] = []
    # Menggunakan ProjectAktivitas yang sudah fix di atas
    aktivitas: List[ProjectAktivitas] = [] 

class ProjectPage(CamelModel):
    total: int
    items: List[Project]

# ===================================================================
# 10. SKEMA AKTIVITAS
# ===================================================================
class Aktivitas(AktivitasBase):
    id: int
    dibuat_pada: datetime
    public_id: UUID
    creator: Optional[UserInTeam] = None
    team: Optional[TeamInProject] = None
    project: Optional[ProjectInUser] = None
    dokumen: List[Dokumen] = []
    daftar_dokumen_wajib: List[DaftarDokumen] = []
    users: List[UserInAktivitas] = []
    tim_terkait: List[Team] = [] # Relasi ke Team
    
    # --- HIERARKI ---
    parent: Optional[AktivitasParent] = None
    children: List[AktivitasChild] = []

class AktivitasPage(CamelModel):
    total: int
    items: List[Aktivitas]

class AktivitasTrendItem(CamelModel):
    month_year: str
    activity_count: int

# ===================================================================
# 11. SKEMA NOTIFIKASI & TOKEN
# ===================================================================
class Token(CamelModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class NotifikasiBase(CamelModel): 
    massage: Optional[str] = None 
    link_to: Optional[str] = None
    title: str
    user_id: int 
    related_activity_id: Optional[int] = None
    related_project_id: Optional[int] = None
    is_read: bool = Field(default=False)

class NotifikasiCreate(NotifikasiBase):
    pass

class Notifikasi(NotifikasiBase):
    id: int
    created_at: datetime
    user: Optional[UserInTeam] = None

class NotifikasiCount(CamelModel):
    count: int

class NotifikasiPage(CamelModel):
    total: int
    items: List[Notifikasi]


# ===================================================================
# SKEMA UNTUK DASHBOARD (BARU)
# ===================================================================
class DashboardStats(CamelModel):
    # Statistik Umum (Kepala/Admin)
    total_pegawai: int = 0
    total_tim: int = 0
    
    # Statistik Tim/Project (Ketua)
    total_anggota_tim: int = 0
    total_project: int = 0
    
    # Statistik Aktivitas (Semua)
    total_aktivitas_bulan_ini: int = 0
    total_aktivitas_saya: int = 0

class DashboardTodoItem(CamelModel):
    id: int # ID dari DaftarDokumen (Checklist Item)
    nama_dokumen: str
    status_pengecekan: bool
    
    # Info Konteks
    aktivitas_id: int
    nama_aktivitas: str
    tanggal_mulai: Optional[date] = None
    nama_tim: Optional[str] = None
    nama_project: Optional[str] = None
    
    # Jenis Todo: 'upload' (Anggota) atau 'validasi' (Ketua)
    jenis_tugas: str
    
# Rebuild model untuk mengatasi circular reference
Team.model_rebuild()
User.model_rebuild()
UserWithTeams.model_rebuild()
TeamDetail.model_rebuild()
Aktivitas.model_rebuild()
Project.model_rebuild()
ProjectAktivitas.model_rebuild()