from fastapi import (FastAPI, Depends, HTTPException, status, Response, File,
                     UploadFile, Form, Query, BackgroundTasks)
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, desc, and_, func, insert, select, update, extract
from sqlalchemy.orm import Session, joinedload
from typing import List,  Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import timedelta, date, datetime
from openpyxl import Workbook

import models, database, schemas, security, uuid, io, os, shutil, uuid, io, zipfile, services_wa

# ===================================================================
# INISIALISASI & KONFIGURASI
# ===================================================================
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

origins = [
    "*"
    ]

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

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    massage: str,
    link_to: str,
    background_tasks: BackgroundTasks,
    activity_id: Optional[int] = None,
    project_id: Optional[int] = None,
    send_whatsapp: bool = True,
    wa_message_override: Optional[str] = None
):
    """
    Membuat notifikasi di DB. Jika send_whatsapp=True dan user memiliki 'nohp',
    akan mengirim notifikasi WA.
    'wa_message_override' akan digunakan sebagai isi pesan WA jika tersedia.
    Jika tidak, 'title' dan 'massage' akan digunakan.
    """
    db_notif = models.Notifikasi(
        user_id=user_id,
        title=title,
        massage=massage,
        link_to=link_to,
        related_activity_id=activity_id,
        related_project_id=project_id,
        is_read=False
    )
    db.add(db_notif)

    user = db.query(models.User).filter(models.User.id == user_id).first()

    # Kirim HANYA jika user punya nohp DAN send_whatsapp=True
    if user and user.nohp and send_whatsapp:

        base_url = "https://sinergi.statsntb.id" 
        full_link = f"{base_url}{link_to}"
        wa_message = ""

        if wa_message_override:
            # GUNAKAN PESAN KUSTOM (jika ada)
            # Kita gunakan placeholder {LINK} agar bisa diganti
            wa_message = wa_message_override.replace("{LINK}", full_link)
        else:
            # GUNAKAN FORMAT LAMA (default)
            wa_message = f"🔔 *Notifikasi SINERGI*\n\n"
            wa_message += f"*{title}*\n"
            wa_message += f"{massage}\n\n"
            wa_message += f"Lihat detail:\n{full_link}"

        # Jalankan di background
        background_tasks.add_task(
            services_wa.send_whatsapp_message,
            phone_number=user.nohp,
            message=wa_message
        )
    
    return db_notif


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

# Di dalam file main.py

# ... (kode lainnya) ...

@app.get("/users/me", response_model=schemas.UserWithTeams, response_model_by_alias=True)
def read_users_me(current_user: models.User = Depends(security.get_current_user), db: Session = Depends(database.get_db)):
    
    # --- LOGIKA UNTUK MENGAMBIL PERAN TIM ---
    teams_with_role = []
    
    # Query untuk mendapatkan semua tim dan peran user terkait dari user_team_link
    user_teams_links = db.query(
        models.Team, 
        models.user_team_link.c.team_role
    ).join(
        models.user_team_link, models.user_team_link.c.team_id == models.Team.id
    ).filter(
        models.user_team_link.c.user_id == current_user.id
    ).all()

    for team, role in user_teams_links:
        teams_with_role.append({
            "id": team.id,
            "nama_tim": team.nama_tim,
            "peran": role # 'member' atau 'operator'
        })
    
    # --- LOGIKA UNTUK MENENTUKAN is_ketua_tim & ketua_tim_aktif ---
    ketua_tim_aktif_list = db.query(models.Team).filter(models.Team.ketua_tim_id == current_user.id).all()
    is_ketua = len(ketua_tim_aktif_list) > 0
    
    # --- BANGUN DICTIONARY RESPONS SECARA MANUAL UNTUK KEAMANAN ---
    # Ini menghindari error konversi otomatis Pydantic yang kompleks
    response_data = {
        "id": current_user.id,
        "username": current_user.username,
        "nama_lengkap": current_user.nama_lengkap,
        "foto_profil_url": current_user.foto_profil_url,
        "is_active": current_user.is_active,
        "sistem_role": current_user.sistem_role,
        "jabatan": current_user.jabatan,
        "nip": current_user.nip,
        "nipbps": current_user.nipbps,
        "gol_akhir": current_user.gol_akhir,
        "tmt_gol": current_user.tmt_gol,
        "tmt_jab": current_user.tmt_jab,
        "status_kepegawaian": current_user.status_kepegawaian,
        "jenis_kelamin": current_user.jenis_kelamin,
        "nohp": current_user.nohp,

        # Data relasi lain yang dibutuhkan oleh skema UserWithTeams
        "created_projects": current_user.created_projects,
        "aktivitas": current_user.aktivitas,
        
        # Data yang kita proses secara manual dari atas
        "teams": teams_with_role,
        "is_ketua_tim": is_ketua,
        "ketua_tim_aktif": ketua_tim_aktif_list,
    }
    
    return response_data

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

@app.put("/api/users/me/profile", response_model=schemas.User)
def update_own_profile(
    profile_data: schemas.ProfileUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Mengizinkan pengguna yang sedang login untuk memperbarui
    nama_lengkap dan nohp mereka sendiri.
    """
    
    # Ambil data dari payload
    update_data = profile_data.dict(exclude_unset=True)
    
    # Update field di objek user
    for key, value in update_data.items():
        if hasattr(current_user, key):
            setattr(current_user, key, value)
        
    db.commit()
    db.refresh(current_user)
    
    # Kita harus return dict manual karena 'teams'
    # (Salin dari read_users_me)
    teams_with_role = []
    user_teams_links = db.query(
        models.Team, 
        models.user_team_link.c.team_role
    ).join(
        models.user_team_link, models.user_team_link.c.team_id == models.Team.id
    ).filter(
        models.user_team_link.c.user_id == current_user.id
    ).all()

    for team, role in user_teams_links:
        teams_with_role.append({
            "id": team.id,
            "nama_tim": team.nama_tim,
            "peran": role
        })
    
    ketua_tim_aktif_list = db.query(models.Team).filter(models.Team.ketua_tim_id == current_user.id).all()
    is_ketua = len(ketua_tim_aktif_list) > 0

    response_data = {
        "id": current_user.id,
        "username": current_user.username,
        "nama_lengkap": current_user.nama_lengkap,
        "foto_profil_url": current_user.foto_profil_url,
        "is_active": current_user.is_active,
        "sistem_role": current_user.sistem_role,
        "jabatan": current_user.jabatan,
        "nip": current_user.nip,
        "nipbps": current_user.nipbps,
        "gol_akhir": current_user.gol_akhir,
        "tmt_gol": current_user.tmt_gol,
        "tmt_jab": current_user.tmt_jab,
        "status_kepegawaian": current_user.status_kepegawaian,
        "jenis_kelamin": current_user.jenis_kelamin,
        "nohp": current_user.nohp, # <-- data ini akan ter-update
        "created_projects": current_user.created_projects,
        "aktivitas": current_user.aktivitas,
        "teams": teams_with_role,
        "is_ketua_tim": is_ketua,
        "ketua_tim_aktif": ketua_tim_aktif_list,
    }
    
    return response_data

# ===================================================================
# ENDPOINT MANAJEMEN ADMIN
# ===================================================================
@app.post("/api/users", response_model=schemas.User, response_model_by_alias=True, dependencies=[Depends(security.require_role(["Superadmin", "Admin"]))])
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = security.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username sudah terdaftar")
    
    hashed_password = security.get_password_hash(user.password)
    
    new_user_data = user.dict()

    new_user_data.pop('password', None)

    new_user = models.User(
        **new_user_data,
        hashed_password=hashed_password
    )

    # new_user = models.User(
    #     username=user.username,
    #     hashed_password=hashed_password,
    #     nama_lengkap=user.nama_lengkap,
    #     sistem_role_id=user.sistem_role_id,
    #     jabatan_id=user.jabatan_id
    # )

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
    users_from_db = query.order_by(models.User.id.desc()).offset(skip).limit(limit).all()

    processed_users = []
    for user in users_from_db:
        teams_with_role = []
        
        # Query untuk mendapatkan peran tim untuk setiap user dalam loop
        user_teams_links = db.query(
            models.Team, 
            models.user_team_link.c.team_role
        ).join(
            models.user_team_link, models.user_team_link.c.team_id == models.Team.id
        ).filter(
            models.user_team_link.c.user_id == user.id
        ).all()

        for team, role in user_teams_links:
            teams_with_role.append({
                "id": team.id,
                "nama_tim": team.nama_tim,
                "peran": role
            })

        user_dict = {
            "id": user.id,
            "username": user.username,
            "nama_lengkap": user.nama_lengkap,
            "foto_profil_url": user.foto_profil_url,
            "is_active": user.is_active,
            "sistem_role": user.sistem_role,
            "jabatan": user.jabatan,
            "created_projects": user.created_projects,
            "aktivitas": user.aktivitas,
            "teams": teams_with_role,

            "nip": user.nip,
            "nipbps": user.nipbps,
            "gol_akhir": user.gol_akhir,
            "tmt_gol": user.tmt_gol,
            "tmt_jab": user.tmt_jab,
            "status_kepegawaian": user.status_kepegawaian,
            "jenis_kelamin": user.jenis_kelamin,
            "nohp": user.nohp
        }
        processed_users.append(user_dict)

    return {"total": total, "items": processed_users}

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
    
    teams_with_role = []
    user_teams_links = db.query(
        models.Team, 
        models.user_team_link.c.team_role
    ).join(
        models.user_team_link, models.user_team_link.c.team_id == models.Team.id
    ).filter(
        models.user_team_link.c.user_id == db_user.id # Gunakan db_user.id
    ).all()

    for team, role in user_teams_links:
        teams_with_role.append({
            "id": team.id,
            "nama_tim": team.nama_tim,
            "peran": role
        })

    # Buat kamus respons manual, sama seperti di get_all_users
    # Ini memastikan semua field baru (nip, nohp) dan teams (dengan peran) disertakan
    user_dict = {
        "id": db_user.id,
        "username": db_user.username,
        "nama_lengkap": db_user.nama_lengkap,
        "foto_profil_url": db_user.foto_profil_url,
        "is_active": db_user.is_active,
        "sistem_role": db_user.sistem_role,
        "jabatan": db_user.jabatan,
        "created_projects": db_user.created_projects,
        "aktivitas": db_user.aktivitas,
        "teams": teams_with_role, # <-- Menggunakan list dict yang sudah benar
        
        # Data baru
        "nip": db_user.nip,
        "nipbps": db_user.nipbps,
        "gol_akhir": db_user.gol_akhir,
        "tmt_gol": db_user.tmt_gol,
        "tmt_jab": db_user.tmt_jab,
        "status_kepegawaian": db_user.status_kepegawaian,
        "jenis_kelamin": db_user.jenis_kelamin,
        "nohp": db_user.nohp
    }

    return user_dict

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
    # 1. Buat instance model Team
    db_team = models.Team(
        nama_tim=team.nama_tim,
        valid_from=team.valid_from,
        valid_until=team.valid_until,
        ketua_tim_id=team.ketua_tim_id,
        warna=team.warna
    )
    db.add(db_team)
    db.flush()  # Gunakan flush untuk mendapatkan ID tim (db_team.id) tanpa mengakhiri transaksi

    # 2. Siapkan data untuk tabel user_team_link
    operator_ids_set = set(team.operator_ids)
    
    # Gabungkan ID ketua dan operator, pastikan tidak ada duplikasi
    all_member_ids = {team.ketua_tim_id} | operator_ids_set if team.ketua_tim_id else operator_ids_set

    links_to_create = []
    if all_member_ids:
        # Cek apakah semua user valid dalam satu query untuk efisiensi
        valid_users = db.query(models.User).filter(models.User.id.in_(all_member_ids)).all()
        valid_user_ids = {user.id for user in valid_users}

        for user_id in valid_user_ids:
            # Peran operator memiliki prioritas lebih tinggi
            role = 'operator' if user_id in operator_ids_set else 'member'
            links_to_create.append({
                "user_id": user_id,
                "team_id": db_team.id,
                "team_role": role
            })

    # 3. Eksekusi bulk insert ke tabel user_team_link jika ada data
    if links_to_create:
        db.execute(insert(models.user_team_link), links_to_create)
    
    # 4. Commit semua perubahan (pembuatan tim dan penambahan anggota) dalam satu transaksi
    db.commit()
    db.refresh(db_team)
    
    return db_team

@app.get("/api/teams", response_model=schemas.TeamPage, response_model_by_alias=True)
def get_all_teams(
    db: Session = Depends(database.get_db),
    skip: int = 0, 
    limit: int = 10, 
    q: Optional[str] = None
):
    query = db.query(models.Team).options(joinedload(models.Team.ketua_tim))
    if q:
        query = query.filter(models.Team.nama_tim.ilike(f"%{q}%"))
    total = query.count()
    teams = query.order_by(desc(models.Team.valid_until), desc(models.Team.id)).offset(skip).limit(limit).all()
    return {"total": total, "items": teams}

@app.get("/api/teams/active", response_model=schemas.TeamPage, response_model_by_alias=True)
def get_active_teams(
    db: Session = Depends(database.get_db),
    skip: int = 0,
    limit: int = 10,
    q: Optional[str] = None
):
    today = date.today()

    query = (
        db.query(models.Team)
        .options(joinedload(models.Team.ketua_tim))
        .filter(
            and_(
                models.Team.valid_from <= today,
                models.Team.valid_until >= today
            )
        )
    )

    if q:
        query = query.filter(models.Team.nama_tim.ilike(f"%{q}%"))

    total = query.count()

    teams = (
        query
        .order_by(models.Team.nama_tim.asc())
        .offset(skip)     
        .limit(limit)       
        .all()
    )
    return {"total": total, "items": teams}


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

    if "operator_ids" in update_data:
        new_operator_ids = set(update_data.pop('operator_ids', []))

        # 1. Hapus semua peran 'operator' yang ada untuk tim ini
        db.execute(
            update(models.user_team_link)
            .where(models.user_team_link.c.team_id == team_id)
            .values(team_role='member')
        )

        # 2. Tetapkan peran 'operator' untuk user yang baru dipilih
        if new_operator_ids:
            db.execute(
                update(models.user_team_link)
                .where(
                    models.user_team_link.c.team_id == team_id,
                    models.user_team_link.c.user_id.in_(new_operator_ids)
                )
                .values(team_role='operator')
            )

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
def add_team_member(team_id: int, user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
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

        # --- LOGIKA NOTIFIKASI BARU: Anggota Ditambahkan ---
        nama_tim = db_team.nama_tim
        link_detail = f"/team/detail/{db_team.id}"
        
        title_notif = f"Anda ditambahkan ke Tim {nama_tim}"
        message_notif = f"Anda sekarang adalah anggota Tim {nama_tim}. Klik untuk melihat detail tim."
        
        create_notification(
            db, 
            user_id=user_id, 
            title=title_notif, 
            massage=message_notif, 
            link_to=link_detail,
            background_tasks=background_tasks
        )
        db.commit() # Commit notifikasi ke database
        # --- END LOGIKA NOTIFIKASI ---

        db.refresh(db_team)

    return db_team

@app.delete("/api/teams/{team_id}/members/{user_id}", response_model=schemas.Team, response_model_by_alias=True, dependencies=[Depends(security.require_role(["Superadmin", "Admin"]))])
def remove_team_member(team_id: int, user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    """Mengeluarkan seorang pengguna dari tim."""
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()

    if not db_team or not db_user:
        raise HTTPException(status_code=404, detail="Tim atau User tidak ditemukan")

    # Cek apakah pengguna benar-benar anggota tim
    if db_user not in db_team.users:
        raise HTTPException(status_code=400, detail="Pengguna bukan anggota tim ini")

    nama_tim = db_team.nama_tim

    if db_user in db_team.users:
        db_team.users.remove(db_user)
        db.commit()

    # --- LOGIKA NOTIFIKASI BARU: Anggota Dihapus ---
    
    title_notif = f"Keanggotaan Tim Berakhir"
    message_notif = f"Anda telah dikeluarkan dari Tim {nama_tim} oleh Administrator. Anda tidak lagi memiliki akses ke proyek dan aktivitas tim tersebut."
    
    create_notification(
        db, 
        user_id=user_id, 
        title=title_notif, 
        massage=message_notif, 
        link_to="/team" ,
        background_tasks=background_tasks
    )
    db.commit() # Commit notifikasi
    # --- END LOGIKA NOTIFIKASI ---
    
    db.refresh(db_team)
    return db_team

@app.get("/api/teams/{team_id}/details", response_model=schemas.TeamDetail, response_model_by_alias=True)
def get_team_details_with_activities(team_id: int, db: Session = Depends(database.get_db)):
    """
    Mengambil detail satu tim, termasuk proyek, anggota (DENGAN PERAN), dan ketua.
    """
    db_team = db.query(models.Team).options(
        joinedload(models.Team.ketua_tim).joinedload(models.User.jabatan),
        joinedload(models.Team.users).joinedload(models.User.jabatan),
        joinedload(models.Team.projects).options(
            joinedload(models.Project.project_leader),
            joinedload(models.Project.aktivitas).joinedload(models.Aktivitas.users)
        )
    ).filter(models.Team.id == team_id).first()
    
    if not db_team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    # --- PENDEKATAN FINAL YANG BENAR ---
    # Tambahkan atribut 'peran' secara dinamis ke setiap objek user SQLAlchemy
    # sebelum Pydantic melakukan validasi dan konversi.
    if db_team.users:
        for user in db_team.users:
            link = db.query(models.user_team_link).filter(
                models.user_team_link.c.user_id == user.id,
                models.user_team_link.c.team_id == team_id
            ).first()
            
            # Menambahkan atribut sementara ke objek model SQLAlchemy
            setattr(user, 'peran', link.team_role if link else 'member')
    # --- AKHIR PENDEKATAN FINAL ---

    # Logika sorting aktivitas tetap sama
    for project in db_team.projects:
        project.aktivitas = sorted(
            project.aktivitas, 
            key=lambda a: a.tanggal_mulai if a.tanggal_mulai else date.min, 
            reverse=True
        )
    
    db_team.aktivitas = []
    
    # Kembalikan objek SQLAlchemy. Pydantic akan menanganinya dengan benar sekarang.
    return db_team

@app.get("/api/teams/{team_id}/aktivitas", response_model=List[schemas.Aktivitas])
def get_aktivitas_by_team_id(team_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    """
    Mengambil semua aktivitas yang terkait dengan ID tim tertentu.
    Aktivitas akan diurutkan dari yang terbaru ke yang terlama.
    """
    # Pastikan tim yang dicari ada di database
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan.")

    # Query database untuk mencari semua aktivitas dengan team_id yang cocok
    # Menggunakan joinedload untuk mengambil data terkait seperti dokumen dan daftar dokumen wajib
    # Menggunakan .order_by() untuk mengurutkan data dari yang terbaru (dibuat pada)
    db_aktivitas = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.dokumen),
        joinedload(models.Aktivitas.daftar_dokumen_wajib),
        joinedload(models.Aktivitas.creator)
    ).filter(models.Aktivitas.team_id == team_id).order_by(models.Aktivitas.dibuat_pada.desc()).all()

    # Mengembalikan daftar aktivitas
    return db_aktivitas

@app.get("/api/aktivitas/trend", response_model=List[schemas.AktivitasTrendItem])
def get_aktivitas_trend(
    db: Session = Depends(database.get_db),
    group_by: str = Query(..., description="Filter group: 'team' atau 'user'."),
    group_id: int = Query(..., description="ID of the Team atau User."),
    months: int = Query(6, description="Number of months history to retrieve.")
):
    """Mengambil tren jumlah aktivitas per bulan untuk group_id tertentu (max 6 bulan)."""
    
    today = date.today()
    # Hitung tanggal mulai 6 bulan ke belakang
    start_date = today.replace(day=1) - timedelta(days=30 * (months - 1)) 
    
    # 1. Build the base query for activity count grouped by year and month
    query = db.query(
        func.to_char(models.Aktivitas.tanggal_mulai, 'YYYY-MM').label('month_year'),
        func.count(models.Aktivitas.id).label('activity_count')
    ).filter(
        models.Aktivitas.tanggal_mulai >= start_date 
    )

    # 2. Apply filtering based on group_by parameter
    if group_by == 'team':
        query = query.filter(models.Aktivitas.team_id == group_id)
    elif group_by == 'user':
        # Join dengan tabel perantara anggota_aktivitas_link
        query = query.join(models.anggota_aktivitas_link).filter(
            models.anggota_aktivitas_link.c.user_id == group_id
        )
    else:
        raise HTTPException(status_code=400, detail="Parameter group_by tidak valid. Gunakan 'team' atau 'user'.")

    # 3. Group the results and order by month
    results = query.group_by('month_year').order_by('month_year').all()

    # 4. Format output (raw data, frontend yang akan mengisi nol)
    trend_data = [
        {"month_year": row.month_year, "activity_count": row.activity_count}
        for row in results
    ]
    
    return trend_data


# ===================================================================
# ENDPOINT UNTUK MANAJEMEN PROJECT
# ===================================================================

@app.post("/api/projects", response_model=schemas.Project, response_model_by_alias=True)
def create_project(project: schemas.ProjectCreate, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db), current_user: models.User = Depends(security.get_current_user)):
    
    team = db.query(models.Team).filter(models.Team.id == project.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    # --- LOGIKA OTORISASI BARU ---
    is_ketua_tim = team.ketua_tim_id == current_user.id
    
    is_operator_query = select(models.user_team_link).where(
        models.user_team_link.c.user_id == current_user.id,
        models.user_team_link.c.team_id == project.team_id,
        models.user_team_link.c.team_role == 'operator'
    )
    is_operator = db.execute(is_operator_query).first() is not None

    if not is_ketua_tim and not is_operator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Anda bukan Ketua Tim atau Operator untuk membuat proyek di tim ini"
        )
    
    project_data = project.dict(by_alias=False)
    db_project = models.Project(**project_data)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # 1. Muat Project dengan relasi Team dan Anggota
    project_with_relations = db.query(models.Project).options(
        joinedload(models.Project.team).joinedload(models.Team.users)
    ).filter(models.Project.id == db_project.id).first()
    
    if not project_with_relations or not project_with_relations.team:
        # Lanjutkan jika tidak ada tim terkait (meskipun skema mengharuskan team_id)
        return db_project 
    
    nama_project = project_with_relations.nama_project
    project_leader_id = project_with_relations.project_leader_id
    link_detail = f"/project/detail/{db_project.id}"
    
    # 2. Definisikan Notifikasi Umum (Untuk Semua Anggota Tim)
    title_umum = f"Project Baru ditambahkan: {nama_project}"
    message_umum = f"Ketua Tim Anda telah membuat Project baru di bawah Tim {project_with_relations.team.nama_tim}."
    
    # 3. Definisikan Notifikasi Khusus (Untuk Project Leader)
    title_leader = f"Anda Project Leader Project {nama_project}!"
    message_leader = "Anda telah ditunjuk sebagai Project Leader."
    
    # 4. Loop dan Kirim Notifikasi
    for user in project_with_relations.team.users:
        if user.id == project_leader_id:
            # Notifikasi Khusus untuk Leader
            create_notification(
                db, 
                user_id=user.id, 
                title=title_leader, 
                massage=message_leader, 
                link_to=link_detail, 
                background_tasks=background_tasks,
                project_id=db_project.id
            )
        else:
            # Notifikasi Umum untuk Anggota
            create_notification(
                db, 
                user_id=user.id, 
                title=title_umum, 
                massage=message_umum, 
                link_to=link_detail, 
                background_tasks=background_tasks,
                project_id=db_project.id
            )
            
    db.commit() # Commit notifikasi
    # --- END LOGIKA NOTIFIKASI ---

    return db_project

@app.get("/api/projects", response_model=schemas.ProjectPage, response_model_by_alias=True)
def get_all_projects(
    db: Session = Depends(database.get_db),
    skip: int = 0,
    limit: int = 10,
    q: Optional[str] = None
):
    """Mendapatkan daftar semua proyek dengan paginasi dan pencarian."""
    query = db.query(models.Project).options(
        joinedload(models.Project.project_leader),
        joinedload(models.Project.team)
    )
    if q:
        query = query.filter(models.Project.nama_project.ilike(f"%{q}%"))
    total = query.count()
    projects = query.order_by(models.Project.id.asc()).offset(skip).limit(limit).all()
    return {"total": total, "items": projects}

@app.get("/api/projects/{project_id}", response_model=schemas.Project, response_model_by_alias=True)
def get_project_by_id(project_id: int, db: Session = Depends(database.get_db)):
    """Mendapatkan detail proyek dan daftar aktivitas aktif yang relevan."""
    
    db_project = db.query(models.Project).options(
        joinedload(models.Project.project_leader),
        joinedload(models.Project.team),
        joinedload(models.Project.dokumen)
    ).filter(models.Project.id == project_id).first()
    
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")

    # Filter dan muat hanya aktivitas yang sedang aktif
    # today = date.today()
    # active_aktivitas = db.query(models.Aktivitas).options(
    #     joinedload(models.Aktivitas.daftar_dokumen_wajib)
    # ).with_parent(db_project).filter(
    #     or_( # Gunakan OR untuk dua kondisi
    #         # Kondisi 1: Aktivitas dengan rentang tanggal
    #         and_(
    #             models.Aktivitas.tanggal_selesai.isnot(None),
    #             models.Aktivitas.tanggal_mulai <= today,
    #             models.Aktivitas.tanggal_selesai >= today
    #         ),
    #         # Kondisi 2: Aktivitas satu hari tanpa jam
    #         and_(
    #             models.Aktivitas.tanggal_selesai.is_(None),
    #             models.Aktivitas.jam_mulai.is_(None),
    #             models.Aktivitas.jam_selesai.is_(None),
    #             models.Aktivitas.tanggal_mulai == today
    #         )
    #     )
    # ).all()
    # db_project.aktivitas = active_aktivitas

    all_aktivitas = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.daftar_dokumen_wajib)
    ).with_parent(db_project).order_by(
        desc(models.Aktivitas.tanggal_mulai)
    ).all()

    db_project.aktivitas = all_aktivitas
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

@app.get("/api/aktivitas", response_model=schemas.AktivitasPage)
def get_all_aktivitas(
    db: Session = Depends(database.get_db), 
    skip: int = 0,
    limit: int = 10,
    q: Optional[str] = None,
    current_user: models.User = Depends(security.get_current_user),
    user_scope: str = 'me',
    month: Optional[int] = None,
    year: Optional[int] = None
):
    query = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.creator),
        joinedload(models.Aktivitas.team)
    )

    # Filter berdasarkan scope (Aktivitas saya / Semua)
    if user_scope == 'me':
        query = query.filter(models.Aktivitas.users.any(id=current_user.id))

    # Filter berdasarkan bulan dan tahun
    if month:
        query = query.filter(extract('month', models.Aktivitas.tanggal_mulai) == month)
    if year:
        query = query.filter(extract('year', models.Aktivitas.tanggal_mulai) == year)

    # Jika ada parameter pencarian 'q'
    if q:
        search_term = f"%{q}%"
        # Lakukan join dengan tabel dokumen agar bisa mencari
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
        ).distinct()

    # --- LOGIKA PAGINATION ---
    
    # 1. Hitung total item yang memenuhi filter/pencarian
    # Karena ada .distinct(), kita harus menggunakan count pada subquery/ID
    if q:
        # Hitung jumlah ID yang berbeda untuk menghindari kesalahan count pada query dengan join dan distinct
        total_query = db.query(func.count(models.Aktivitas.id.distinct())).select_from(query.subquery())
        total = total_query.scalar()
    else:
        # Jika tidak ada distinct, count sederhana lebih cepat
        total = query.count()
        
    # 2. Ambil data dengan sorting, offset, dan limit
    aktivitas_items = (
        query
        .order_by(models.Aktivitas.id.desc())
        .offset(skip)              # 👈 Terapkan skip (offset)
        .limit(limit)              # 👈 Terapkan limit
        .all()
    )

    # 3. Kembalikan hasil dalam format paging
    return {"total": total, "items": aktivitas_items}

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

@app.get("/api/public/aktivitas/{public_id}", response_model=schemas.Aktivitas)
def get_public_aktivitas_detail(
    public_id: uuid.UUID,
    db: Session = Depends(database.get_db)
):
    """
    Endpoint publik untuk mengambil detail aktivitas menggunakan public_id (UUID).
    Tidak memerlukan otentikasi.
    """
    # Query aktivitas berdasarkan public_id
    aktivitas = db.query(models.Aktivitas).options(
        # Load semua relasi yang ingin Anda tampilkan di halaman publik
        joinedload(models.Aktivitas.project),
        joinedload(models.Aktivitas.team),
        joinedload(models.Aktivitas.users).joinedload(models.User.jabatan), # Load anggota & jabatan
        joinedload(models.Aktivitas.dokumen)
    ).filter(models.Aktivitas.public_id == public_id).first()

    if not aktivitas:
        raise HTTPException(status_code=404, detail="Aktivitas tidak ditemukan")
    
    # Skema 'schemas.Aktivitas' Anda akan digunakan untuk merespons
    return aktivitas
  
@app.post("/api/aktivitas", response_model=schemas.Aktivitas)
def create_aktivitas(
    aktivitas: schemas.AktivitasCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
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
    
    # LOGIKA PENGIRIMAN NOTIFIKASI
    if db_aktivitas.users:
        # Muat relasi Team dan Project
        aktivitas_with_relations = db.query(models.Aktivitas).options(
            joinedload(models.Aktivitas.team),
            joinedload(models.Aktivitas.project) # <-- Ini sudah ada
        ).filter(models.Aktivitas.id == db_aktivitas.id).first()

        # --- KUMPULKAN INFO UNTUK WA ---
        
        nama_aktivitas = aktivitas_with_relations.nama_aktivitas
        nama_tim = aktivitas_with_relations.team.nama_tim if aktivitas_with_relations.team else "Tim Tidak Diketahui"
        
        # V TAMBAHKAN NAMA PROYEK V
        nama_project = aktivitas_with_relations.project.nama_project if aktivitas_with_relations.project else "Tanpa Proyek"
        # ^ AKHIR BLOK TAMBAHAN ^
        
        link_detail = f"/aktivitas/detail/{db_aktivitas.id}"

        # 1. Format String Pelaksanaan (Tanggal)
        pelaksanaan_str = ""
        tgl_mulai = aktivitas_with_relations.tanggal_mulai
        tgl_selesai = aktivitas_with_relations.tanggal_selesai
        
        if tgl_mulai:
            pelaksanaan_str = f"🗓️ {tgl_mulai.strftime('%d %B %Y')}"
            if tgl_selesai and tgl_selesai != tgl_mulai:
                pelaksanaan_str += f" - {tgl_selesai.strftime('%d %B %Y')}"
        else:
            pelaksanaan_str = "🗓️ Tanggal belum ditentukan"

        # 2. Format String Pelaksanaan (Waktu)
        jam_mulai = aktivitas_with_relations.jam_mulai
        jam_selesai = aktivitas_with_relations.jam_selesai
        
        if jam_mulai:
            jam_str = f"⏰ {jam_mulai.strftime('%H.%M')}"
            if jam_selesai:
                jam_str += f" - {jam_selesai.strftime('%H.%M')} WITA"
            else:
                jam_str += " WITA"
            pelaksanaan_str += f"\n{jam_str}"
        
        # --- AKHIR INFO WA ---

        # Kirim notifikasi ke setiap pengguna yang terlibat
        for user in db_aktivitas.users:
            
            # --- PERBAIKAN: Template WA yang Disempurnakan ---
            wa_msg_template = (
                f"🔔 *Notifikasi SINERGI: Aktivitas Baru*\n\n"
                f"Halo {user.nama_lengkap}!\n"
                f"Anda telah ditambahkan ke aktivitas baru:\n\n"
                f"👥 *Tim*:\n{nama_tim}\n\n"
                f"💼 *Project*:\n{nama_project}\n\n" 
                f"📝 *Nama Aktivitas*:\n{nama_aktivitas}\n\n"
                f"*Pelaksanaan*:\n{pelaksanaan_str}\n\n"
                f"Lihat Detail:\n"
                f"{{LINK}}\n\n"  # Placeholder
                f"Aplikasi Sinergi\n" # <-- Menambahkan footer
                f"BPS Provinsi Nusa Tenggara Barat"
            )
            
            # Pesan In-App (Singkat)
            app_title = f"Aktivitas Baru: {nama_aktivitas}"
            app_massage = f"Anda ditambahkan ke aktivitas ini oleh {current_user.nama_lengkap}."
            
            create_notification(
                db, 
                user_id=user.id, 
                title=app_title,
                massage=app_massage,
                link_to=link_detail,
                background_tasks=background_tasks,
                activity_id=db_aktivitas.id, 
                project_id=db_aktivitas.project_id,
                send_whatsapp=True,
                wa_message_override=wa_msg_template # <-- Mengirim template kustom
            )
        
        db.commit()
    # END: LOGIKA PENGIRIMAN NOTIFIKASI

    print(f"Aktivitas berhasil disimpan dengan ID: {db_aktivitas.id}")
    print(f"Total anggota yang tersimpan di database: {len(db_aktivitas.users)}")
    print("--- Proses selesai ---")
    return db_aktivitas

@app.get("/api/aktivitas/download-excel", response_class=StreamingResponse)
def download_aktivitas_excel(
    db: Session =Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user),
    user_scope: str = 'me',
    month: Optional[int] = None,
    year: Optional[int] = None
):
    query = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.project),
        joinedload(models.Aktivitas.team)
    )

    if user_scope == 'me': 
        query = query.filter(models.Aktivitas.users.any(id=current_user.id))

    if month:
        query = query.filter(extract('month', models.Aktivitas.tanggal_mulai) == month)
    if year:
        query = query.filter(extract('year', models.Aktivitas.tanggal_mulai) == year)

    # Ambil semua data yang cocok (tanpa pagination)
    aktivitas_list = query.order_by(models.Aktivitas.tanggal_mulai.desc()).all()

    # Buat File Excel di Memori
    wb = Workbook()
    ws = wb.active
    ws.title = "Daftar Aktivitas"
    
    # Buat Header
    headers = ["Nama Aktivitas", "Nama Proyek", "Tim", "Bukti Dukung (Link)"]
    ws.append(headers)

    # 3. Isi Data
    base_url = "https://sinergi.statsntb.id" # URL frontend Anda
    for aktivitas in aktivitas_list:
        # Menggunakan nama relasi dari model Anda
        project_name = aktivitas.project.nama_project if aktivitas.project else "N/A"
        team_name = aktivitas.team.nama_tim if aktivitas.team else "N/A"
        link = f"{base_url}/public/aktivitas/{aktivitas.public_id}"
        
        ws.append([
            aktivitas.nama_aktivitas,
            project_name,
            team_name,
            link
        ])

    # Simpan ke stream (buffer)
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0) # Pindahkan kursor ke awal file

    # 5. Kembalikan sebagai file download
    filename = f"aktivitas_{user_scope}_{year}_{month}.xlsx" if month and year else f"aktivitas_{user_scope}.xlsx"
    return StreamingResponse(
        stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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
def delete_aktivitas(
    aktivitas_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    aktivitas_to_delete = db.query(models.Aktivitas).filter(models.Aktivitas.id == aktivitas_id).first()

    if aktivitas_to_delete is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aktivitas tidak ditemukan.")

    if aktivitas_to_delete.dokumen:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tidak dapat menghapus aktivitas karena masih terdapat dokumen terkait. Harap hapus semua dokumen terkait terlebih dahulu."
        )

    nama_aktivitas = aktivitas_to_delete.nama_aktivitas
    users_terlibat = aktivitas_to_delete.team.users if aktivitas_to_delete.team else []

    # --- LOGIKA NOTIFIKASI: SEBELUM PENGHAPUSAN ---
    if users_terlibat:
        title_notif = f"Aktivitas Dihapus: {nama_aktivitas}"
        message_notif = (
            f"Aktivitas '{nama_aktivitas}' telah dihapus. "
            "Semua data terkait telah dihilangkan."
        )
        
        # Kirim notifikasi ke semua anggota yang terlibat
        for user in users_terlibat:
            create_notification(
                db, 
                user_id=user.id, 
                title=title_notif, 
                massage=message_notif, 
                background_tasks=background_tasks,
                link_to="/dashboard", 
                activity_id=None,
                send_whatsapp=False
            )
        db.commit() # Commit notifikasi
    # --- END LOGIKA NOTIFIKASI ---

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
    link_data: schemas.DokumenCreate,
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
        path_atau_url=link_data.path_atau_url
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
        path_atau_url=link_data.path_atau_url
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Memperbarui status pengecekan (true/false) untuk sebuah item di daftar dokumen.
    Hanya bisa dilakukan oleh ketua tim dari aktivitas terkait.
    """
    # Cari item checklist di database, lakukan join untuk mengambil data tim terkait
    db_item = db.query(models.DaftarDokumen).options(
        joinedload(models.DaftarDokumen.aktivitas).joinedload(models.Aktivitas.team)
    ).filter(models.DaftarDokumen.id == item_id).first()

    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Item checklist tidak ditemukan"
        )

    # Ambil status lama sebelum diubah
    old_status = db_item.status_pengecekan
    new_status = status_update.status_pengecekan

    # Validasi Keamanan: Pastikan pengguna adalah ketua tim
    # Pastikan ada aktivitas dan tim yang tertaut sebelum memeriksa
    if not db_item.aktivitas or not db_item.aktivitas.team:
          raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Item checklist tidak terhubung dengan tim yang valid"
        )

    # Jika validasi berhasil, perbarui status
    db_item.status_pengecekan = status_update.status_pengecekan
    db.commit()

    # --- LOGIKA NOTIFIKASI ---
    if old_status != new_status and db_item.dokumen_id:
        
        # A. Tentukan Konten Notifikasi
        nama_dokumen = db_item.nama_dokumen
        nama_aktivitas = db_item.aktivitas.nama_aktivitas
        link_detail = f"/aktivitas/detail/{db_item.aktivitas_id}"
        
        if new_status is True:
            title_notif = f"Dokumen Disetujui: {nama_dokumen}"
            message_notif = f"Dokumen Anda di aktivitas '{nama_aktivitas}' telah divalidasi dan disetujui oleh {current_user.nama_lengkap}."
        else: # new_status is False (Pembatalan persetujuan)
            title_notif = f"Persetujuan Dibatalkan: {nama_dokumen}"
            message_notif = f"Persetujuan dokumen Anda di aktivitas '{nama_aktivitas}' dibatalkan oleh {current_user.nama_lengkap} untuk diperbaiki."
        
        # B. Kirim Notifikasi ke semua Anggota Aktivitas
        if db_item.aktivitas.users:
            for user in db_item.aktivitas.users:
                # Kirim ke semua anggota aktivitas
                create_notification(
                    db,
                    user_id=user.id,
                    title=title_notif,
                    massage=message_notif,
                    background_tasks=background_tasks,
                    link_to=link_detail,
                    activity_id=db_item.aktivitas_id,
                    send_whatsapp=False
                )
            db.commit()
            
    # --- END LOGIKA NOTIFIKASI ---

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

# ===================================================================
# ENDPOINT UNTUK NOTIFKIKASI
# ===================================================================

# Endpoint 1: GET /api/notifications/count (Untuk Polling Badge)
@app.get("/api/notifications/count")
def get_unread_notification_count(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Menghitung jumlah notifikasi yang belum dibaca untuk pengguna."""
    
    unread_count = db.query(models.Notifikasi).filter(
        models.Notifikasi.user_id == current_user.id,
        models.Notifikasi.is_read == False
    ).count()
    
    return {"count": unread_count}

# Endpoint 2: GET /api/notifications (Untuk Dropdown List)
@app.get("/api/notifications/header", response_model=List[schemas.Notifikasi]) 
def get_header_notifications(
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(security.get_current_user), 
    limit: int = 15
):
    """Mengambil daftar notifikasi terbaru (list saja) untuk header dropdown."""
    
    notifications = db.query(models.Notifikasi).options(
        joinedload(models.Notifikasi.user) 
    ).filter(
        models.Notifikasi.user_id == current_user.id
    ).order_by(
        models.Notifikasi.created_at.desc() 
    ).limit(limit).all()
    
    return notifications


# Endpoint 2b: GET /api/notifications (Paginated untuk Halaman View All)
# Endpoint ini yang sebelumnya bermasalah karena dipanggil oleh header. Sekarang hanya untuk NotifikasiView.
@app.get("/api/notifications", response_model=schemas.NotifikasiPage) 
def get_user_notifications_paginated(
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(security.get_current_user), 
    skip: int = 0,
    limit: int = 20, 
    is_read: Optional[bool] = Query(None) 
):
    """Mengambil daftar notifikasi terbaru untuk pengguna dengan dukungan paginasi."""
    
    query = db.query(models.Notifikasi).options(
        joinedload(models.Notifikasi.user) 
    ).filter(
        models.Notifikasi.user_id == current_user.id
    )
    
    if is_read is not None:
        query = query.filter(models.Notifikasi.is_read == is_read)

    total = query.count()
    
    notifications = query.order_by(
        models.Notifikasi.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {"total": total, "items": notifications} 


# Endpoint 3: PATCH /api/notifications/{id}/read (Untuk Mark as Read)
@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Menandai notifikasi sebagai sudah dibaca."""
    
    # 1. Cari notifikasi, pastikan dimiliki oleh user saat ini
    db_notification = db.query(models.Notifikasi).filter(
        models.Notifikasi.id == notification_id,
        models.Notifikasi.user_id == current_user.id
    ).first()
    
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan")
    
    # 2. Update status
    db_notification.is_read = True
    db.commit()
    db.refresh(db_notification)
    
    return {"message": "Notifikasi berhasil ditandai sebagai sudah dibaca"}

@app.patch("/api/notifications/mark-all-read")
def mark_all_as_read(current_user: models.User = Depends(security.get_current_user), db: Session = Depends(database.get_db)):
    """Menandai SEMUA notifikasi pengguna sebagai sudah dibaca."""
    db.query(models.Notifikasi).filter(
        models.Notifikasi.user_id == current_user.id,
        models.Notifikasi.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    
    db.commit()
    return {"message": "Semua notifikasi berhasil ditandai sebagai sudah dibaca"}