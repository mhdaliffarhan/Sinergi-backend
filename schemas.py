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

    # 3. Cek Aturan: Harus '62' dan 12-14 digit total
    # (62 + 10-12 digit sisa = 12-14 total)
    if not re.match(r"^62\d{9,12}$", nohp_numeric):
         raise ValueError(
            "Nomor HP harus diawali 62 dan memiliki 12-14 digit (misal: 62812...)"
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
# SKEMA UNTUK PERAN & JABATAN
# ===================================================================
class Jabatan(CamelModel):
    id: int
    nama_jabatan: str


class SistemRole(CamelModel):
    id: int
    nama_role: str


# ===================================================================
# SKEMA UNTUK DOKUMEN
# ===================================================================
class DokumenBase(CamelModel):
    keterangan: str
    tipe: str
    path_atau_url: Optional[str] = None
    nama_file_asli: Optional[str] = None
    tipe_file_mime: Optional[str] = None


class DokumenCreate(DokumenBase):
    pass


class Dokumen(DokumenBase):
    id: int
    diunggah_pada: datetime
    aktivitas_id: Optional[int] = None
    project_id: Optional[int] = None


# ===================================================================
# SKEMA UNTUK DAFTAR DOKUMEN WAJIB
# ===================================================================
class DaftarDokumen(CamelModel):
    id: int
    nama_dokumen: str
    dokumen_id: Optional[int] = None
    dokumen_terkait: Optional[Dokumen] = None
    status_pengecekan: bool


# ===================================================================
# SKEMA UNTUK USER
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

# Tambahan: Skema untuk user yang terlibat dalam aktivitas
class UserInAktivitas(CamelModel):
    id: int
    username: str
    nama_lengkap: Optional[str] = None
    foto_profil_url: Optional[str] = None
    jabatan_id: int


# Skema untuk Team yang akan digunakan di dalam User
class TeamInUser(CamelModel):
    id: int
    nama_tim: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None

# Skema ini mewarisi dari TeamInUser dan menambahkan field 'peran'
class TeamInUserWithRole(TeamInUser):
    peran: str

# Skema untuk Project yang akan digunakan di dalam User
class ProjectInUser(CamelModel):
    id: int
    nama_project: str
    project_leader_id: Optional[int] = None
    project_leader: Optional[UserInTeam] = None
    
# Tambahan: Skema untuk aktivitas yang akan digunakan di dalam User
class AktivitasInUser(CamelModel):
    id: int
    nama_aktivitas: str
    tanggal_mulai: Optional[date] = None
    tanggal_selesai: Optional[date] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None

# Base dan Create skema untuk User
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

    class Config:
        from_attributes = True

    # V TAMBAHKAN BLOK VALIDATOR INI V

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
        # Memanggil helper yang kita buat di atas
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


# Skema utama untuk menampilkan User secara penuh
class User(UserBase):
    id: int
    is_active: bool
    sistem_role: SistemRole
    jabatan: Optional[Jabatan] = None
    teams: List[TeamInUserWithRole] = []
    created_projects: List[ProjectInUser] = []
    aktivitas: List[AktivitasInUser] = [] 


# Skema khusus untuk endpoint "me" yang menampilkan informasi lebih detail
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
# SKEMA UNTUK TEAM
# ===================================================================
class TeamInProject(CamelModel):
    id: int
    nama_tim: str
    ketua_tim_id: Optional[int] = None
    warna: Optional[str] = None
    ketua_tim: Optional[UserInTeam] = None

class ProjectInTeam(CamelModel):
    id: int
    nama_project: str
    project_leader: Optional[UserInProject] = None
    aktivitas: List[AktivitasInTeam] = []

class AktivitasInTeam(CamelModel):
    id: int
    nama_aktivitas: str
    deskripsi: Optional[str] = None
    tanggal_mulai: Optional[date] = None
    tanggal_selesai: Optional[date] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None
    melibatkan_kepala: bool
    users: List[UserInAktivitas] = []

class TeamBase(CamelModel):
    id: int
    nama_tim: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    ketua_tim_id: Optional[int] = None
    warna: Optional[str] = None

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


# Skema utama untuk menampilkan Team secara penuh
class Team(TeamBase):
    id: int
    ketua_tim: Optional[UserInTeam] = None
    users: List[UserInTeam] = []


class TeamPage(CamelModel):
    total: int
    items: List[Team]


# ===================================================================
# SKEMA UNTUK PROJECT
# ===================================================================
class ProjectBase(CamelModel):
    nama_project: str
    team_id: Optional[int] = None
    project_leader_id: int


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(CamelModel):
    nama_project: Optional[str] = None
    team_id: Optional[int] = None
    project_leader_id: Optional[int] = None

class ProjectAktivitas(CamelModel):
    id: int
    nama_aktivitas: str
    daftar_dokumen_wajib: List[DaftarDokumen] = []
    tanggal_mulai: Optional[date] = None
    tanggal_selesai: Optional[date] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None


class Project(ProjectBase):
    id: int
    project_leader: Optional[UserInProject] = None
    team: Optional[TeamInProject] = None
    dokumen: List[Dokumen] = []
    aktivitas: List[ProjectAktivitas] = []


class ProjectPage(CamelModel):
    total: int
    items: List[Project]


# ===================================================================
# SKEMA UNTUK AKTIVITAS
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


class StatusPengecekanUpdate(CamelModel):
    status_pengecekan: bool


class AktivitasCreate(AktivitasBase):
    daftar_dokumen_wajib: List[str] = []
    anggota_aktivitas_ids: List[int] = []


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

class AktivitasPage(CamelModel):
    total: int
    items: List[Aktivitas]

class AktivitasTrendItem(CamelModel):
    month_year: str
    activity_count: int

# ===================================================================
# SKEMA UNTUK AUTENTIKASI
# ===================================================================
class Token(CamelModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None

# ===================================================================
# SKEMA UNTUK NOTIFIKASI
# ===================================================================
class NotifikasiBase(CamelModel): 
    # Kolom opsional saat notifikasi dibuat
    massage: Optional[str] = None 
    link_to: Optional[str] = None
    
    # Kolom wajib
    title: str
    user_id: int 
    
    # Foreign Keys
    related_activity_id: Optional[int] = None
    related_project_id: Optional[int] = None
    
    # Status
    is_read: bool = Field(default=False)


class NotifikasiCreate(NotifikasiBase):
    pass


class Notifikasi(NotifikasiBase):
    id: int
    created_at: datetime
    pass

class NotifikasiCount(CamelModel):
    count: int

class NotifikasiPage(CamelModel):
    total: int
    items: List[Notifikasi]

# Rebuild model untuk mengatasi circular reference jika ada
Team.model_rebuild()
User.model_rebuild()
UserWithTeams.model_rebuild()
TeamDetail.model_rebuild()
Aktivitas.model_rebuild()
Project.model_rebuild()