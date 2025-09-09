from fastapi import (FastAPI, Depends, HTTPException, status, Response, File,
                     UploadFile, Form, Query)
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, desc, and_
from sqlalchemy.orm import Session, joinedload  
from typing import List,  Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import timedelta, date, datetime

import models, database, schemas, security
import os, shutil, uuid, io, zipfile

# ===================================================================
# INISIALISASI & KONFIGURASI
# ===================================================================
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOKUMEN_DIRECTORY = "./dokumen"
UPLOAD_PROFILE_PIC_DIR = "./profile-picture"

if not os.path.exists(DOKUMEN_DIRECTORY):
    os.makedirs(DOKUMEN_DIRECTORY)
app.mount("/dokumen", StaticFiles(directory="dokumen"), name="dokumen")

if not os.path.exists(UPLOAD_PROFILE_PIC_DIR):
    os.makedirs(UPLOAD_PROFILE_PIC_DIR)
app.mount("/profile-picture", StaticFiles(directory="profile-picture"), name="profile-picture")


def get_document_path(db: Session, project_id: Optional[int] = None, aktivitas_id: Optional[int] = None):
    """
    Fungsi pembantu untuk membangun jalur penyimpanan file berdasarkan
    aktivitas atau proyek.
    """
    if not project_id and not aktivitas_id:
        raise HTTPException(status_code=400, detail="project_id atau aktivitas_id harus diberikan.")

    folder_tahun = str(date.today().year)
    folder_tim = None
    folder_proyek = None
    folder_aktivitas = None

    if aktivitas_id:
        # Muat aktivitas dan relasinya ke tim
        aktivitas = db.query(models.Aktivitas).options(
            joinedload(models.Aktivitas.team)
        ).filter(models.Aktivitas.id == aktivitas_id).first()
        
        if not aktivitas:
            raise HTTPException(status_code=404, detail="Data aktivitas tidak ditemukan.")
        if not aktivitas.team:
            raise HTTPException(status_code=404, detail="Tim untuk aktivitas ini tidak ditemukan.")
        
        # Ambil project secara terpisah
        if not aktivitas.project_id:
            raise HTTPException(status_code=404, detail="Aktivitas tidak terhubung ke proyek manapun.")
            
        project = db.query(models.Project).filter(models.Project.id == aktivitas.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Proyek untuk aktivitas ini tidak ditemukan.")

        folder_tim = aktivitas.team.nama_tim.replace(' ', '-')
        folder_proyek = project.nama_project.replace(' ', '-')
        folder_aktivitas = f"{aktivitas.tanggal_mulai.strftime('%y%m%d')}_{aktivitas.nama_aktivitas.replace(' ','-')}"
        
    elif project_id:
        # Muat proyek dan relasinya ke tim
        project = db.query(models.Project).options(
            joinedload(models.Project.team)
        ).filter(models.Project.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Data proyek tidak ditemukan.")
        if not project.team:
            raise HTTPException(status_code=404, detail="Tim untuk proyek ini tidak ditemukan.")

        folder_tim = project.team.nama_tim.replace(' ', '-')
        folder_proyek = project.nama_project.replace(' ', '-')

    # Membangun jalur hierarkis
    base_path = os.path.join(DOKUMEN_DIRECTORY, folder_tahun, folder_tim, folder_proyek)
    
    if folder_aktivitas:
        base_path = os.path.join(base_path, folder_aktivitas)
        
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
        
    return base_path

# ===================================================================
# ENDPOINT OTENTIKASI & PENGGUNA
# ===================================================================
@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = security.get_user(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username atau password salah")
    
    token = security.create_access_token(data={"sub": user.username})
    content = {"accessToken": token, "tokenType": "bearer"}
    return JSONResponse(content=content)

@app.get("/users/me", response_model=schemas.UserWithTeams, response_model_by_alias=True)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user

@app.post("/api/{user_id}/upload-photo")
def upload_profile_photo(user_id: int, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    # cek ekstensi file
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Format foto tidak valid. Gunakan JPG/PNG")

    # buat folder kalau belum ada
    os.makedirs(UPLOAD_PROFILE_PIC_DIR, exist_ok=True)

    # simpan file
    file_path = f"{UPLOAD_PROFILE_PIC_DIR}/{user_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # update DB
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    user.foto_profil_url = file_path
    db.commit()
    db.refresh(user)

    return {"message": "Foto profil berhasil diunggah", "foto_profil_url": user.foto_profil_url}

@app.delete("/api/{user_id}/delete-photo")
def delete_profile_photo(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    if user.foto_profil_url:
        file_path = user.foto_profil_url.lstrip("/")
        if os.path.exists(file_path):
            os.remove(file_path)

        user.foto_profil_url = None
        db.commit()
        db.refresh(user)

    return {"message": "Foto profil berhasil dihapus"}

@app.put("/api/users/{user_id}/password")
def update_password(
    user_id: int,
    password_data: schemas.PasswordUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # Pastikan user hanya bisa ganti password dirinya sendiri
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak diizinkan mengganti password user lain"
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan")

    # Verifikasi password lama
    if not security.verify_password(password_data.old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password lama salah")

    # Update password baru
    hashed_new_password = security.get_password_hash(password_data.new_password)
    user.hashed_password = hashed_new_password
    db.commit()

    return {"message": "Password berhasil diperbarui"}

# ===================================================================
# ENDPOINT MANAJEMEN ADMIN
# ===================================================================
@app.post("/api/users", response_model=schemas.User, response_model_by_alias=True, dependencies=[Depends(security.require_role(["Superadmin", "Admin"]))])
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = security.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username sudah terdaftar")
    
    hashed_password = security.get_password_hash(user.password)
    
    new_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        nama_lengkap=user.nama_lengkap,
        sistem_role_id=user.sistem_role_id,
        jabatan_id=user.jabatan_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/api/users", response_model=schemas.UserPage, response_model_by_alias=True)
def get_all_users(
    db: Session = Depends(database.get_db),
    skip: int = 0, 
    limit: int = 10, 
    search: Optional[str] = None
):
    query = db.query(models.User).options(
        joinedload(models.User.sistem_role),
        joinedload(models.User.jabatan)
    )
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.User.nama_lengkap.ilike(search_term),
                models.User.username.ilike(search_term)
            )
        ).distinct()

    total = query.count()
    users = query.order_by(models.User.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": users}

@app.put("/api/users/{user_id}", response_model=schemas.User, response_model_by_alias=True, dependencies=[Depends(security.require_role(["Superadmin"]))])
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(database.get_db)):
    """Memperbarui data pengguna (hanya Superadmin)."""
    
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    
    # Ambil data yang dikirim sebagai dictionary snake_case, abaikan field yang kosong (None)
    update_data = user_update.dict(exclude_unset=True)

    # Perbarui setiap field di objek database
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    # Simpan perubahan
    db.commit()
    db.refresh(db_user)
    
    return db_user

# --- ENDPOINT UNTUK MENGHAPUS USER ---
@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(security.require_role(["Superadmin"]))])
def delete_user(user_id: int, db: Session = Depends(database.get_db)):
    """Menghapus pengguna berdasarkan ID (hanya Superadmin)."""
    
    # Cari pengguna di database
    user_query = db.query(models.User).filter(models.User.id == user_id)
    db_user = user_query.first()
    
    if db_user is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
    # Hapus pengguna
    user_query.delete(synchronize_session=False)
    db.commit()
    
    # Kembalikan respons tanpa konten
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/api/teams", response_model=schemas.Team, response_model_by_alias=True, dependencies=[Depends(security.require_role(["Superadmin", "Admin"]))])
def create_team(team: schemas.TeamCreate, db: Session = Depends(database.get_db)):
    db_team = models.Team(
        nama_tim=team.nama_tim,
        valid_from=team.valid_from,
        valid_until=team.valid_until,
        ketua_tim_id=team.ketua_tim_id,
        warna=team.warna
    )

    # Pastikan ketua_tim_id ada dan bukan null
    if team.ketua_tim_id:
        ketua_tim_user = db.query(models.User).filter(models.User.id == team.ketua_tim_id).first()
        if not ketua_tim_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ketua Tim tidak ditemukan."
            )
        
        # Tambahkan objek User ke relationship 'users' tim
        db_team.users.append(ketua_tim_user)
        # SQLAlchemy akan secara otomatis membuat entri di user_team_link

    # 3. Simpan Tim ke database
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

@app.get("/api/teams", response_model=schemas.TeamPage, response_model_by_alias=True)
def get_all_teams(
    db: Session = Depends(database.get_db),
    skip: int = 0, 
    limit: int = 10, 
    search: Optional[str] = None
):
    query = db.query(models.Team).options(joinedload(models.Team.ketua_tim))
    if search:
        query = query.filter(models.Team.nama_tim.ilike(f"%{search}%"))
    total = query.count()
    teams = query.order_by(desc(models.Team.valid_until), desc(models.Team.id)).offset(skip).limit(limit).all()
    return {"total": total, "items": teams}

@app.get("/api/teams/active", response_model=list[schemas.Team], response_model_by_alias=True)
def get_active_teams(
    db: Session = Depends(database.get_db)
):
    today = date.today()
    teams = (
        db.query(models.Team)
        .filter(
            and_(
                models.Team.valid_from <= today,
                models.Team.valid_until >= today
            )
        )
        .order_by(models.Team.nama_tim.asc())
        .all()
    )
    return teams

@app.put("/api/teams/{team_id}", response_model=schemas.Team, response_model_by_alias=True,
          dependencies=[Depends(security.require_role(["Superadmin", "Admin"]))])
def update_team(team_id: int, team_update: schemas.TeamUpdate, db: Session = Depends(database.get_db)):
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    update_data = team_update.dict(exclude_unset=True, by_alias=False)

    # Jika ada ketua_tim_id baru
    if "ketua_tim_id" in update_data and update_data["ketua_tim_id"] is not None:
        new_ketua_id = update_data["ketua_tim_id"]

        # cek apakah user sudah ada di anggota tim via relasi
        ketua_sudah_anggota = any(u.id == new_ketua_id for u in db_team.users)

        # kalau belum → tambahkan
        if not ketua_sudah_anggota:
            ketua_user = db.query(models.User).filter(models.User.id == new_ketua_id).first()
            if not ketua_user:
                raise HTTPException(status_code=404, detail="Ketua Tim tidak ditemukan.")
            db_team.users.append(ketua_user)

    # Update field lain
    for key, value in update_data.items():
        setattr(db_team, key, value)

    db.commit()
    db.refresh(db_team)
    return db_team


@app.delete("/api/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(security.require_role(["Superadmin"]))])
def delete_team(team_id: int, db: Session = Depends(database.get_db)):
    """Menghapus tim (hanya Superadmin), tetapi hanya jika tidak memiliki aktivitas terkait."""
    
    # 1. Cari tim yang akan dihapus
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()

    if db_team is None:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    # 2. Cek apakah tim memiliki aktivitas terkait
    if db_team.aktivitas:
        raise HTTPException(
            status_code=400,
            detail="Gagal menghapus tim. Tim ini masih memiliki aktivitas terkait."
        )

    # 3. Jika tidak ada aktivitas terkait, hapus tim
    # Anda harus menghapus data di tabel perantara secara manual (jika ada) sebelum menghapus tim utama
    db.delete(db_team)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- ENDPOINT BARU UNTUK MANAJEMEN ANGGOTA TIM ---

@app.get("/api/teams/{team_id}", response_model=schemas.Team, response_model_by_alias=True)
def get_team_details(team_id: int, db: Session = Depends(database.get_db)):
    """Mengambil detail satu tim, termasuk daftar anggotanya."""
    
    # Gunakan joinedload untuk mengambil data anggota sekaligus
    # Gunakan joinedload untuk mengambil data anggota sekaligus
    db_team = db.query(models.Team).options(
        joinedload(models.Team.users).joinedload(models.User.jabatan),
        joinedload(models.Team.users).joinedload(models.User.sistem_role)
    ).filter(models.Team.id == team_id).first()
    
    if not db_team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")
    
    return db_team

@app.post("/api/teams/{team_id}/members", response_model=schemas.Team, response_model_by_alias=True, dependencies=[Depends(security.require_role(["Superadmin", "Admin" ]))])
def add_team_member(team_id: int, user_id: int, db: Session = Depends(database.get_db)):
    """Menambahkan seorang pengguna ke dalam tim."""
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()

    if not db_team or not db_user:
        raise HTTPException(status_code=404, detail="Tim atau User tidak ditemukan")

    # Cek agar tidak duplikat
    if db_user in db_team.users:
        raise HTTPException(status_code=400, detail="Pengguna sudah menjadi anggota tim ini")

    if db_user not in db_team.users:
        db_team.users.append(db_user)
        db.commit()
        db.refresh(db_team)

    return db_team

@app.delete("/api/teams/{team_id}/members/{user_id}", response_model=schemas.Team, response_model_by_alias=True, dependencies=[Depends(security.require_role(["Superadmin", "Admin"]))])
def remove_team_member(team_id: int, user_id: int, db: Session = Depends(database.get_db)):
    """Mengeluarkan seorang pengguna dari tim."""
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()

    if not db_team or not db_user:
        raise HTTPException(status_code=404, detail="Tim atau User tidak ditemukan")

    # Cek apakah pengguna benar-benar anggota tim
    if db_user not in db_team.users:
        raise HTTPException(status_code=400, detail="Pengguna bukan anggota tim ini")

    if db_user in db_team.users:
        db_team.users.remove(db_user)
        db.commit()
        db.refresh(db_team)

    return db_team

@app.get("/api/teams/{team_id}/details", response_model=schemas.TeamDetail, response_model_by_alias=True)
def get_team_details_with_activities(team_id: int, db: Session = Depends(database.get_db)):
    """
    Mengambil detail satu tim, termasuk proyek (dengan aktivitas di dalamnya), anggota, dan ketua.
    """
    db_team = db.query(models.Team).options(
        joinedload(models.Team.ketua_tim).joinedload(models.User.jabatan),
        joinedload(models.Team.users).joinedload(models.User.jabatan),
        
        # Eager load projects dan nested activities di dalamnya
        joinedload(models.Team.projects).joinedload(models.Project.aktivitas).joinedload(models.Aktivitas.users)
        
    ).filter(models.Team.id == team_id).first()
    
    if not db_team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    # Opsional: Urutkan aktivitas di dalam setiap proyek
    for project in db_team.projects:
        project.aktivitas = sorted(project.aktivitas, key=lambda a: a.tanggal_mulai if a.tanggal_mulai else date.min)
    
    # Hapus properti aktivitas yang ada di level tim
    # Karena kita akan menampilkan aktivitas per proyek
    db_team.aktivitas = []
    
    return db_team

# ===================================================================
# ENDPOINT UNTUK MANAJEMEN PROJECT
# ===================================================================

@app.post("/api/projects", response_model=schemas.Project, response_model_by_alias=True)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(database.get_db)):
    """Membuat proyek baru (hanya Superadmin atau Admin)."""
    project_data = project.dict(by_alias=False)
    db_project = models.Project(**project_data)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/api/projects", response_model=schemas.ProjectPage, response_model_by_alias=True)
def get_all_projects(
    db: Session = Depends(database.get_db),
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None
):
    """Mendapatkan daftar semua proyek dengan paginasi dan pencarian."""
    query = db.query(models.Project).options(
        joinedload(models.Project.project_leader),
        joinedload(models.Project.team)
    )
    if search:
        query = query.filter(models.Project.nama_project.ilike(f"%{search}%"))
    total = query.count()
    projects = query.order_by(models.Project.id.asc()).offset(skip).limit(limit).all()
    return {"total": total, "items": projects}

@app.get("/api/projects/{project_id}", response_model=schemas.Project, response_model_by_alias=True)
def get_project_by_id(project_id: int, db: Session = Depends(database.get_db)):
    """Mendapatkan detail proyek dan daftar aktivitas aktif yang relevan."""
    
    # Ambil data proyek secara utuh
    db_project = db.query(models.Project).options(
        joinedload(models.Project.project_leader),
        joinedload(models.Project.team),
        joinedload(models.Project.dokumen)
    ).filter(models.Project.id == project_id).first()
    
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")

    # Filter dan muat hanya aktivitas yang sedang aktif
    today = date.today()
    active_aktivitas = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.daftar_dokumen_wajib)
    ).with_parent(db_project).filter(
        or_( # Gunakan OR untuk dua kondisi
            # Kondisi 1: Aktivitas dengan rentang tanggal
            and_(
                models.Aktivitas.tanggal_selesai.isnot(None),
                models.Aktivitas.tanggal_mulai <= today,
                models.Aktivitas.tanggal_selesai >= today
            ),
            # Kondisi 2: Aktivitas satu hari tanpa jam
            and_(
                models.Aktivitas.tanggal_selesai.is_(None),
                models.Aktivitas.jam_mulai.is_(None),
                models.Aktivitas.jam_selesai.is_(None),
                models.Aktivitas.tanggal_mulai == today
            )
        )
    ).all()

    # Tambahkan daftar aktivitas yang sudah difilter ke objek proyek
    db_project.aktivitas = active_aktivitas

    return db_project

@app.put("/api/projects/{project_id}", response_model=schemas.Project, response_model_by_alias=True)
def update_project(project_id: int, project_update: schemas.ProjectUpdate, db: Session = Depends(database.get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")
    
    update_data = project_update.dict(exclude_unset=True, by_alias=False)
    for key, value in update_data.items():
        setattr(db_project, key, value)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(security.require_role(["Superadmin", "Admin"]))])
def delete_project(project_id: int, db: Session = Depends(database.get_db)):
    """Menghapus proyek (hanya Superadmin atau Admin)."""
    project_query = db.query(models.Project).filter(models.Project.id == project_id)
    db_project = project_query.first()

    if db_project is None:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")
    
    project_query.delete(synchronize_session=False)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/api/sistem-roles", response_model=List[schemas.SistemRole])
def get_all_sistem_roles(db: Session = Depends(database.get_db)):
    """Mengembalikan semua peran sistem yang tersedia."""
    roles_db = db.query(models.SistemRole).all()
    # Konversi manual
    return [schemas.SistemRole.from_orm(role) for role in roles_db]

@app.get("/api/jabatan", response_model=List[schemas.Jabatan])
def get_all_jabatan(db: Session = Depends(database.get_db)):
    """Mengembalikan semua jabatan yang tersedia."""
    jabatan_db = db.query(models.Jabatan).all()
    # Konversi manual
    return [schemas.Jabatan.from_orm(j) for j in jabatan_db]

@app.get("/api/aktivitas", response_model=List[schemas.Aktivitas])
def get_all_aktivitas(
    db: Session = Depends(database.get_db), 
    q: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user)
):
    # Query dasar dengan eager loading dokumen
    query = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.creator),
        joinedload(models.Aktivitas.team)
    )

    # Jika ada parameter pencarian 'q'
    if q:
        search_term = f"%{q}%"
        # Lakukan join dengan tabel dokumen agar bisa mencari di sana
        query = query.outerjoin(models.Dokumen)
        # Filter berdasarkan beberapa kolom sekaligus
        query = query.filter(
            or_(
                models.Aktivitas.nama_aktivitas.ilike(search_term),
                models.Aktivitas.deskripsi.ilike(search_term),
                models.Aktivitas.team.has(models.Team.nama_tim.ilike(search_term)),
                models.Dokumen.keterangan.ilike(search_term),
                models.Dokumen.nama_file_asli.ilike(search_term)
            )
        ).distinct() # Gunakan distinct agar aktivitas tidak muncul berulang

    # Urutkan berdasarkan ID terbaru dan ambil semua hasilnya
    semua_aktivitas = query.order_by(models.Aktivitas.id.desc()).all()
    return semua_aktivitas

@app.get("/api/aktivitas/kepala", response_model=List[schemas.Aktivitas])
def get_aktivitas_kepala(
    db: Session = Depends(database.get_db)):
    
    query = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.team),
        joinedload(models.Aktivitas.project)
    ).filter(
        models.Aktivitas.melibatkan_kepala == True
    ).order_by(
        models.Aktivitas.tanggal_mulai.asc()
    )
    return query.all()
    
@app.post("/api/aktivitas", response_model=schemas.Aktivitas)
def create_aktivitas(
    aktivitas: schemas.AktivitasCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    print("--- Memulai proses pembuatan aktivitas ---")
    print(f"Data payload yang diterima: {aktivitas.dict()}")

    # Ekstrak data yang akan digunakan untuk membuat instance model Aktivitas
    aktivitas_data = {
        "nama_aktivitas": aktivitas.nama_aktivitas,
        "deskripsi": aktivitas.deskripsi,
        "tanggal_mulai": aktivitas.tanggal_mulai,
        "tanggal_selesai": aktivitas.tanggal_selesai,
        "jam_mulai": aktivitas.jam_mulai,
        "jam_selesai": aktivitas.jam_selesai,
        "team_id": aktivitas.team_id,
        "project_id": aktivitas.project_id,
        "melibatkan_kepala": aktivitas.melibatkan_kepala
    }
    
    # Set creator_user_id dari pengguna yang sedang login
    aktivitas_data['creator_user_id'] = current_user.id
    
    # Buat instance model Aktivitas dengan data yang sudah difilter
    db_aktivitas = models.Aktivitas(**aktivitas_data)

    # Tambahkan anggota tim ke objek aktivitas
    anggota_aktivitas_ids = list(set(aktivitas.anggota_aktivitas_ids)) # Gunakan set untuk menghapus duplikat
    
    print(f"Daftar final ID anggota yang akan ditambahkan: {anggota_aktivitas_ids}")

    if anggota_aktivitas_ids:
        anggota_tim = db.query(models.User).filter(models.User.id.in_(anggota_aktivitas_ids)).all()
        for user in anggota_tim:
            db_aktivitas.users.append(user)
        print(f"Berhasil melampirkan {len(anggota_tim)} anggota ke aktivitas.")
    else:
        print("Tidak ada anggota yang ditambahkan ke aktivitas ini.")


    # Tambahkan daftar dokumen wajib
    for nama_dok in aktivitas.daftar_dokumen_wajib:
        if nama_dok:
            db_aktivitas.daftar_dokumen_wajib.append(
                models.DaftarDokumen(nama_dokumen=nama_dok, status_pengecekan=False)
            )

    # Simpan ke database
    db.add(db_aktivitas)
    db.commit()
    db.refresh(db_aktivitas)
    
    print(f"Aktivitas berhasil disimpan dengan ID: {db_aktivitas.id}")
    print(f"Total anggota yang tersimpan di database: {len(db_aktivitas.users)}")
    print("--- Proses selesai ---")
    return db_aktivitas

# --- ENDPOINT MENGAMBIL DETAIL AKTIVITAS ---
@app.get("/api/aktivitas/{aktivitas_id}", response_model=schemas.Aktivitas)
def get_aktivitas_by_id(aktivitas_id: int, db: Session = Depends(database.get_db)):
    # Query database untuk mencari aktivitas dengan ID yang sesuai
    db_aktivitas = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.dokumen),
        joinedload(models.Aktivitas.daftar_dokumen_wajib)
    ).filter(models.Aktivitas.id == aktivitas_id).first()
    
    # Jika aktivitas tidak ditemukan, kirim error 404
    if db_aktivitas is None:
        raise HTTPException(status_code=404, detail="Aktivitas tidak ditemukan")
        
    # Jika ditemukan, kembalikan datanya
    return db_aktivitas

# --- ENDPOINT MENGUPDATE AKTIVITAS ---
@app.put("/api/aktivitas/{aktivitas_id}", response_model=schemas.Aktivitas)
def update_aktivitas(
    aktivitas_id: int, 
    aktivitas: schemas.AktivitasCreate, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(security.get_current_user)
):
    """Memperbarui aktivitas yang ada beserta anggota tim dan dokumen wajibnya."""
    db_aktivitas = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.daftar_dokumen_wajib),
        joinedload(models.Aktivitas.users)
    ).filter(models.Aktivitas.id == aktivitas_id).first()
    if db_aktivitas is None:
        raise HTTPException(status_code=404, detail="Aktivitas tidak ditemukan")

    # Logika untuk mengambil ID user Kepala Kantor
    kepala_kantor_id = None
    JABATAN_KEPALA_KANTOR_ID = 1 # Ganti dengan ID jabatan Kepala Kantor yang sesuai
    kepala_kantor = db.query(models.User).filter(
        models.User.jabatan_id == JABATAN_KEPALA_KANTOR_ID
    ).first()
    if kepala_kantor:
        kepala_kantor_id = kepala_kantor.id

    # 1. Update data utama aktivitas
    update_data = aktivitas.dict(exclude_unset=True)
    anggota_aktivitas_ids = update_data.pop('anggota_aktivitas_ids', [])
    daftar_dokumen_wajib = update_data.pop('daftar_dokumen_wajib', [])
    melibatkan_kepala_kantor = update_data.pop('melibatkan_kepala_kantor', False)
    update_data.pop('use_date_range', None)
    update_data.pop('use_time', None)
    
    # Update field-field utama
    for key, value in update_data.items():
        setattr(db_aktivitas, key, value)
    
    # 2. Update anggota tim yang terlibat (Hubungan Many-to-Many)
    final_anggota_ids = set(anggota_aktivitas_ids)
    if melibatkan_kepala_kantor and kepala_kantor_id:
        final_anggota_ids.add(kepala_kantor_id)

    existing_members = {user.id for user in db_aktivitas.users}
    
    members_to_add = final_anggota_ids - existing_members
    members_to_remove = existing_members - final_anggota_ids

    # Hapus anggota yang tidak dipilih lagi
    if members_to_remove:
        members_to_remove_obj = db.query(models.User).filter(models.User.id.in_(members_to_remove)).all()
        for user in members_to_remove_obj:
            if user in db_aktivitas.users:
                db_aktivitas.users.remove(user)

    # Tambahkan anggota baru
    if members_to_add:
        members_to_add_obj = db.query(models.User).filter(models.User.id.in_(members_to_add)).all()
        for user in members_to_add_obj:
            db_aktivitas.users.append(user)
    
    # 3. Update daftar dokumen wajib
    existing_doc_names = {doc.nama_dokumen for doc in db_aktivitas.daftar_dokumen_wajib}
    incoming_doc_names = set(daftar_dokumen_wajib)
    
    docs_to_delete = [doc for doc in db_aktivitas.daftar_dokumen_wajib if doc.nama_dokumen not in incoming_doc_names]
    for doc in docs_to_delete:
        db.delete(doc)

    docs_to_add = incoming_doc_names - existing_doc_names
    for doc_name in docs_to_add:
        new_doc = models.DaftarDokumen(nama_dokumen=doc_name, aktivitas_id=aktivitas_id)
        db.add(new_doc)
            
    db.commit()
    db.refresh(db_aktivitas)
    return db_aktivitas

# --- ENDPOINT MENGHAPUS AKTIVITAS ---
@app.delete("/api/aktivitas/{aktivitas_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_aktivitas(aktivitas_id: int, db: Session = Depends(database.get_db)):
    aktivitas_to_delete = db.query(models.Aktivitas).filter(models.Aktivitas.id == aktivitas_id).first()

    if aktivitas_to_delete is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aktivitas tidak ditemukan.")

    if aktivitas_to_delete.dokumen:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tidak dapat menghapus aktivitas karena masih terdapat dokumen terkait. Harap hapus semua dokumen terkait terlebih dahulu."
        )

    # Hapus semua entri di tabel perantara 'anggota_aktivitas' secara manual
    db.query(models.anggota_aktivitas_link).filter(models.anggota_aktivitas_link.c.aktivitas_id == aktivitas_id).delete(synchronize_session=False)

    # Hapus semua entri di tabel 'daftar_dokumen' secara manual
    db.query(models.DaftarDokumen).filter(models.DaftarDokumen.aktivitas_id == aktivitas_id).delete(synchronize_session=False)

    # Hapus aktivitas itu sendiri
    db.delete(aktivitas_to_delete)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- ENDPOINT UPLOAD DOKUMEN ---
@app.post("/api/aktivitas/{aktivitas_id}/dokumen", response_model=schemas.Dokumen)
def create_dokumen_untuk_aktivitas(
    aktivitas_id: int,
    keterangan: str = Form(...),
    checklist_item_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    # Inisialisasi variabel di luar blok try untuk mencegah UnboundLocalError
    file_location = None

    try:
        # Cek aktivitas
        aktivitas = db.query(models.Aktivitas).filter(models.Aktivitas.id == aktivitas_id).first()
        if not aktivitas:
            raise HTTPException(status_code=404, detail="Aktivitas tidak ditemukan")

        # Panggil fungsi pembantu untuk mendapatkan direktori
        target_dir = get_document_path(db, aktivitas_id=aktivitas_id)
        
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_location = os.path.join(target_dir, unique_filename)

        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        
        db_dokumen = models.Dokumen(
            aktivitas_id=aktivitas_id,
            keterangan=keterangan,
            tipe='FILE',
            path_atau_url=file_location,
            nama_file_asli=file.filename,
            tipe_file_mime=file.content_type
        )
        db.add(db_dokumen)
        db.commit()
        db.refresh(db_dokumen)

        if checklist_item_id:
            db_checklist_item = db.query(models.DaftarDokumen).filter(models.DaftarDokumen.id == checklist_item_id).first()
            if db_checklist_item:
                db_checklist_item.status_pengecekan = False
                db_checklist_item.dokumen_id = db_dokumen.id
                db.commit()
        
        return db_dokumen

    except HTTPException as e:
        # Menangkap error HTTP dan meneruskannya
        raise e
    except Exception as e:
        # Menangkap error umum, mencetak ke konsol server, dan menghapus file jika sudah dibuat
        print(f"Error saat mengunggah dokumen di aktivitas {aktivitas_id}: {e}")
        if file_location and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan di server: {str(e)}")

# --- ENDPOINT MENAMBAHKAN LINK ---
@app.post("/api/aktivitas/{aktivitas_id}/link", response_model=schemas.Dokumen)
def add_link_untuk_aktivitas(
    aktivitas_id: int,
    link_data: schemas.DokumenCreate, # Kita akan gunakan kembali skema ini
    db: Session = Depends(database.get_db)
):
    # Cek dulu apakah aktivitasnya ada
    aktivitas = db.query(models.Aktivitas).filter(models.Aktivitas.id == aktivitas_id).first()
    if not aktivitas:
        raise HTTPException(status_code=404, detail="Aktivitas tidak ditemukan")

    # Buat entri dokumen baru dengan tipe 'LINK'
    db_dokumen = models.Dokumen(
        aktivitas_id=aktivitas_id,
        keterangan=link_data.keterangan,
        tipe='LINK',
        path_atau_url=link_data.pathAtauUrl # Kita asumsikan frontend mengirim URL di field ini
    )

    db.add(db_dokumen)
    db.commit()
    db.refresh(db_dokumen)
    
    return db_dokumen

# --- ENDPOINT UNGGAH DOKUMEN UNTUK PROYEK ---
@app.post("/api/projects/{project_id}/dokumen", response_model=schemas.Dokumen)
def create_dokumen_untuk_proyek(
    project_id: int,
    keterangan: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    """
    Mengunggah file ke sebuah proyek.
    File akan disimpan di jalur: /dokumen/{tahun}/{nama_tim}/{nama_proyek}/
    """
    # 1. Cari proyek berdasarkan ID
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")

    # 2. Dapatkan jalur penyimpanan baru menggunakan fungsi pembantu
    target_dir = get_document_path(db, project_id=project_id)
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_location = os.path.join(target_dir, unique_filename)

    # 3. Simpan file fisik
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
    finally:
        file.file.close()

    # 4. Buat entri dokumen baru di database dengan project_id
    db_dokumen = models.Dokumen(
        project_id=project_id,
        keterangan=keterangan,
        tipe='FILE',
        path_atau_url=file_location,
        nama_file_asli=file.filename,
        tipe_file_mime=file.content_type
    )
    db.add(db_dokumen)
    db.commit()
    db.refresh(db_dokumen)
    
    return db_dokumen

# --------------------------------------------------------------------

# --- ENDPOINT TAMBAH LINK UNTUK PROYEK ---
@app.post("/api/projects/{project_id}/links", response_model=schemas.Dokumen)
def add_link_untuk_proyek(
    project_id: int,
    link_data: schemas.DokumenCreate,
    db: Session = Depends(database.get_db)
):
    """
    Menambahkan link ke sebuah proyek.
    """
    # 1. Cari proyek berdasarkan ID
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")

    # 2. Buat entri dokumen baru dengan tipe 'LINK'
    db_dokumen = models.Dokumen(
        project_id=project_id,
        keterangan=link_data.keterangan,
        tipe='LINK',
        path_atau_url=link_data.pathAtauUrl
    )
    
    db.add(db_dokumen)
    db.commit()
    db.refresh(db_dokumen)
    
    return db_dokumen

# --- ENDPOINT BARU UNTUK MENGGANTI FILE DI CHECKLIST ---
@app.post("/api/checklist/{item_id}/replace", response_model=schemas.Dokumen)
def replace_checklist_dokumen(
    item_id: int,
    old_file_action: str = Form(...), # Menerima 'hapus' atau 'unlink'
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    # 1. Cari item checklist yang akan diupdate
    db_checklist_item = db.query(models.DaftarDokumen).filter(models.DaftarDokumen.id == item_id).first()
    if not db_checklist_item:
        raise HTTPException(status_code=404, detail="Item checklist tidak ditemukan")

    # Simpan ID dokumen lama sebelum diubah
    old_dokumen_id = db_checklist_item.dokumen_id

    # 2. Simpan file baru dan buat entri dokumen baru (logika sama seperti upload)
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_location = os.path.join(DOKUMEN_DIRECTORY, unique_filename)
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
    finally:
        file.file.close()
    
    new_db_dokumen = models.Dokumen(
        aktivitas_id=db_checklist_item.aktivitas_id,
        keterangan=db_checklist_item.nama_dokumen,
        tipe='FILE',
        path_atau_url=file_location,
        nama_file_asli=file.filename,
        tipe_file_mime=file.content_type
    )
    db.add(new_db_dokumen)
    db.flush() # Gunakan flush untuk mendapatkan ID dari dokumen baru

    # 3. Update item checklist untuk menunjuk ke dokumen baru
    db_checklist_item.dokumen_id = new_db_dokumen.id

    # 4. Proses dokumen lama berdasarkan aksi yang dipilih
    if old_dokumen_id and old_file_action == 'hapus':
        old_db_dokumen = db.query(models.Dokumen).filter(models.Dokumen.id == old_dokumen_id).first()
        if old_db_dokumen:
            # Hapus file fisik
            if os.path.exists(old_db_dokumen.path_atau_url):
                os.remove(old_db_dokumen.path_atau_url)
            # Hapus catatan dari database
            db.delete(old_db_dokumen)
    
    # 5. Commit semua perubahan
    db.commit()
    db.refresh(new_db_dokumen)
    
    return new_db_dokumen

# --- ENDPOIN MENGHAPUS DOKUMEN ---
@app.delete("/api/dokumen/{dokumen_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dokumen(dokumen_id: int, db: Session = Depends(database.get_db)):
    db_dokumen = db.query(models.Dokumen).filter(models.Dokumen.id == dokumen_id).first()
    
    if db_dokumen is None:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    # --- LOGIKA BARU: PERBARUI CHECKLIST ---
    db_checklist_item = db.query(models.DaftarDokumen).filter(models.DaftarDokumen.dokumen_id == dokumen_id).first()
    
    # 3. Jika ada, reset status dan tautannya
    if db_checklist_item:
        db_checklist_item.status_pengecekan = False 
        db_checklist_item.dokumen_id = None
        
    if db_dokumen.tipe == 'FILE':
        file_path = db_dokumen.path_atau_url
        if os.path.exists(file_path):
            os.remove(file_path)
            
    db.delete(db_dokumen)
    db.commit()
    
    # 4. Kembalikan respons tanpa konten
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ENDPOINT UNTUK MANAJEMEN CHECKLIST DOKUMEN
@app.patch("/api/daftar_dokumen/{item_id}/cek", response_model=schemas.DaftarDokumen, response_model_by_alias=True)
def update_status_pengecekan(
    item_id: int,
    status_update: schemas.StatusPengecekanUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Memperbarui status pengecekan (true/false) untuk sebuah item di daftar dokumen.
    Hanya bisa dilakukan oleh ketua tim dari aktivitas terkait.
    """
    # 1. Cari item checklist di database, lakukan join untuk mengambil data tim terkait
    db_item = db.query(models.DaftarDokumen).options(
        joinedload(models.DaftarDokumen.aktivitas).joinedload(models.Aktivitas.team)
    ).filter(models.DaftarDokumen.id == item_id).first()

    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Item checklist tidak ditemukan"
        )

    # 2. Validasi Keamanan: Pastikan pengguna adalah ketua tim
    # Pastikan ada aktivitas dan tim yang tertaut sebelum memeriksa
    if not db_item.aktivitas or not db_item.aktivitas.team:
          raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Item checklist tidak terhubung dengan tim yang valid"
        )

    # 3. Jika validasi berhasil, perbarui status
    db_item.status_pengecekan = status_update.status_pengecekan
    db.commit()
    db.refresh(db_item)
    
    # 4. Kembalikan data yang sudah diperbarui
    return db_item

# --- ENDPOINT BARU UNTUK UNDUH/PREVIEW DOKUMEN ---
@app.get("/api/dokumen/{dokumen_id}/download")
def download_dokumen(
    dokumen_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Mengirim file ke pengguna dengan nama file aslinya dan menyarankan preview.
    """
    db_dokumen = db.query(models.Dokumen).filter(models.Dokumen.id == dokumen_id).first()

    if db_dokumen is None or db_dokumen.tipe != 'FILE' or not os.path.exists(db_dokumen.path_atau_url):
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    # --- PERBAIKAN DI SINI ---
    # Atur header Content-Disposition secara manual untuk 'inline'
    headers = {
        'Content-Disposition': f'inline; filename="{db_dokumen.nama_file_asli}"'
    }
    
    # Kirim file sebagai respons dengan header yang sudah diatur
    return FileResponse(
        path=db_dokumen.path_atau_url,
        media_type=db_dokumen.tipe_file_mime,
        headers=headers
    )

# --- ENDPOINTUNTUK UNDUH SEMUA DOKUMEN DALAM SATU AKTIVITAS ---
@app.get("/api/aktivitas/{aktivitas_id}/download-all")
def download_all_dokumen(
    aktivitas_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Mengunduh semua dokumen bertipe FILE dari sebuah aktivitas dalam bentuk .zip.
    """
    db_aktivitas = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.dokumen)
    ).filter(models.Aktivitas.id == aktivitas_id).first()

    if not db_aktivitas:
        raise HTTPException(status_code=404, detail="Aktivitas tidak ditemukan")

    files_to_zip = [doc for doc in db_aktivitas.dokumen if doc.tipe == 'FILE' and os.path.exists(doc.path_atau_url)]

    # --- VALIDASI DOKUMEN KOSONG ---
    if not files_to_zip:
        raise HTTPException(status_code=404, detail="Tidak ada file yang bisa diunduh untuk aktivitas ini.")

    # --- PROSES ZIPPING YANG LEBIH EFISIEN ---
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for doc in files_to_zip:
            zip_file.write(doc.path_atau_url, doc.nama_file_asli)
    
    zip_buffer.seek(0)

    zip_filename = f"{db_aktivitas.nama_aktivitas.replace(' ', '_')}.zip"
    
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/x-zip-compressed",
        headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'}
    )

# ===================================================================
# ENDPOINT BARU UNTUK KALENDER TIM
# ===================================================================

@app.get("/api/kalender/events", response_model=List[schemas.Aktivitas])
def get_calendar_events(
    db: Session = Depends(database.get_db),
    team_ids: Optional[str] = Query(None, description="Daftar ID tim yang dipisahkan oleh koma."),
):
    """
    Mengambil daftar semua aktivitas yang relevan untuk tampilan kalender.
    Jika team_ids diberikan, akan memfilter berdasarkan anggota tim.
    """
    query = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.users),
        joinedload(models.Aktivitas.team)
    )

    if team_ids:
        try:
            team_id_list = [int(id_str) for id_str in team_ids.split(',') if id_str.isdigit()]
            if team_id_list:
                # Mengambil ID pengguna dari tim yang dipilih
                user_ids_in_teams = db.query(models.user_team_link.c.user_id).filter(
                    models.user_team_link.c.team_id.in_(team_id_list)
                ).all()
                unique_user_ids = {user_id for (user_id,) in user_ids_in_teams}
                
                # Menemukan aktivitas yang terkait dengan anggota tim tersebut
                query = query.join(models.anggota_aktivitas_link).filter(
                    models.anggota_aktivitas_link.c.user_id.in_(unique_user_ids)
                ).distinct()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format team_ids tidak valid.")
    
    return query.all()


@app.get("/api/kalender/timeline", response_model=List[dict])
def get_timeline_data(
    db: Session = Depends(database.get_db),
    team_ids: Optional[str] = Query(None, description="Daftar ID tim yang dipisahkan oleh koma."),
    start_date: date = Query(..., description="Tanggal mulai rentang timeline (YYYY-MM-DD)."),
    end_date: date = Query(..., description="Tanggal selesai rentang timeline (YYYY-MM-DD).")
):
    """
    Mengambil data timeline yang sudah diolah dari backend, termasuk penugasan lane.
    """
    query = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.users).joinedload(models.User.jabatan),
        joinedload(models.Aktivitas.team)
    ).filter(
        or_(
            and_(
                models.Aktivitas.tanggal_mulai <= end_date,
                models.Aktivitas.tanggal_selesai >= start_date
            ),
            and_(
                models.Aktivitas.tanggal_mulai.between(start_date, end_date),
                models.Aktivitas.tanggal_selesai.is_(None)
            )
        )
    ).order_by(models.Aktivitas.tanggal_mulai)

    if team_ids:
        try:
            team_id_list = [int(id_str) for id_str in team_ids.split(',') if id_str.isdigit()]
            if team_id_list:
                user_ids_in_teams = db.query(models.user_team_link.c.user_id).filter(
                    models.user_team_link.c.team_id.in_(team_id_list)
                ).all()
                unique_user_ids = {user_id for (user_id,) in user_ids_in_teams}
                query = query.join(models.anggota_aktivitas_link).filter(
                    models.anggota_aktivitas_link.c.user_id.in_(unique_user_ids)
                ).distinct()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format team_ids tidak valid.")

    aktivitas = query.all()
    
    # Kumpulkan daftar pegawai unik
    pegawai_map = {}
    for a in aktivitas:
        for user in a.users:
            if user.id not in pegawai_map:
                pegawai_map[user.id] = {
                    "id": user.id,
                    "namaLengkap": user.nama_lengkap,
                    "aktivitas": []
                }
    
    # Tetapkan lane dan tambahkan ke setiap pegawai
    for pegawai_id, pegawai_data in pegawai_map.items():
        pegawai_events = []
        for a in aktivitas:
            if any(u.id == pegawai_id for u in a.users):
                pegawai_events.append({
                    "id": a.id,
                    "title": a.nama_aktivitas,
                    "start": a.tanggal_mulai,
                    "end": a.tanggal_selesai if a.tanggal_selesai else a.tanggal_mulai,
                    "start_time": str(a.jam_mulai) if a.jam_mulai else None,
                    "end_time": str(a.jam_selesai) if a.jam_selesai else None,
                    "backgroundColor": a.team.warna if a.team else "#2563eb",
                    "tanggalMulai": a.tanggal_mulai,
                    "tanggalSelesai": a.tanggal_selesai,
                })

        # Logika penugasan lane yang dipindahkan dari frontend
        sorted_events = sorted(pegawai_events, key=lambda e: e['start'])
        lanes = []
        for event in sorted_events:
            assigned_lane = -1
            for i, lane in enumerate(lanes):
                can_fit = True
                for placed_event in lane:
                    start1 = event['start']
                    end1 = event['end']
                    start2 = placed_event['start']
                    end2 = placed_event['end']
                    # Logika tumpang tindih
                    if max(start1, start2) <= min(end1, end2):
                        can_fit = False
                        break
                if can_fit:
                    assigned_lane = i
                    break
            
            if assigned_lane == -1:
                lanes.append([event])
                event['lane'] = len(lanes)
            else:
                lanes[assigned_lane].append(event)
                event['lane'] = assigned_lane + 1

        pegawai_data['aktivitas'] = sorted_events

    return list(pegawai_map.values())

# Endpoint untuk mengambil semua aktivitas yang melibatkan pengguna tertentu
@app.get("/api/users/{user_id}/aktivitas", response_model=List[schemas.Aktivitas])
def get_user_aktivitas(user_id: int, db: Session = Depends(database.get_db)):
    """
    Mengambil semua aktivitas di mana pengguna dengan user_id terlibat.
    """
    # Mengambil aktivitas yang terkait dengan user, dengan eager loading team untuk kalender
    user_aktivitas = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.team)
    ).join(models.anggota_aktivitas_link).filter(
        models.anggota_aktivitas_link.c.user_id == user_id
    ).order_by(models.Aktivitas.tanggal_mulai.desc()).all()
    
    return user_aktivitas

# Endpoint untuk mengambil semua dokumen wajib yang harus diselesaikan pengguna
@app.get("/api/users/{user_id}/dokumen-wajib", response_model=List[schemas.DaftarDokumen])
def get_user_dokumen_wajib(user_id: int, db: Session = Depends(database.get_db)):
    """
    Mengambil daftar dokumen wajib yang terkait dengan aktivitas pengguna.
    """
    dokumen_wajib = db.query(models.DaftarDokumen).options(
        joinedload(models.DaftarDokumen.aktivitas),
        joinedload(models.DaftarDokumen.aktivitas).joinedload(models.Aktivitas.team)
    ).join(models.Aktivitas).join(models.anggota_aktivitas_link).filter(
        models.anggota_aktivitas_link.c.user_id == user_id
    ).order_by(models.Aktivitas.tanggal_mulai.desc()).all()

    return dokumen_wajib

# Endpoint untuk mengambil semua dokumen wajib dari sebuah tim
@app.get("/api/teams/{team_id}/dokumen-wajib-team", response_model=List[schemas.DaftarDokumen])
def get_team_dokumen_wajib(team_id: int, db: Session = Depends(database.get_db)):
    """
    Mengambil daftar dokumen wajib dari semua aktivitas di sebuah tim.
    """
    dokumen_wajib = db.query(models.DaftarDokumen).options(
        joinedload(models.DaftarDokumen.aktivitas),
        joinedload(models.DaftarDokumen.aktivitas).joinedload(models.Aktivitas.team)
    ).join(models.Aktivitas).filter(
        models.Aktivitas.team_id == team_id
    ).order_by(models.Aktivitas.tanggal_mulai.desc()).all()

    return dokumen_wajib

@app.get("/api/kalender/events", response_model=List[schemas.Aktivitas])
def get_calendar_events(
    db: Session = Depends(database.get_db),
    team_ids: Optional[str] = Query(None, description="Daftar ID tim yang dipisahkan oleh koma."),
):
    """
    Mengambil daftar semua aktivitas yang relevan untuk tampilan kalender.
    Jika team_ids diberikan, akan memfilter berdasarkan tim tersebut.
    """
    query = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.users),
        joinedload(models.Aktivitas.team)
    )

    if team_ids:
        try:
            team_id_list = {int(id_str) for id_str in team_ids.split(',') if id_str.isdigit()}
            if team_id_list:
                query = query.filter(models.Aktivitas.team_id.in_(team_id_list))
        except ValueError:
            raise HTTPException(status_code=400, detail="Format team_ids tidak valid.")
    
    return query.all()