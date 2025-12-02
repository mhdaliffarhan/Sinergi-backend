import random
from datetime import date, timedelta, time, datetime
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import model dari file models.py Anda
# Pastikan nama file models.py sesuai, jika tidak ubah 'models' di bawah
from models import Base, User, Team, Project, Aktivitas, Dokumen
# Ganti URL database sesuai konfigurasi local Anda
# Contoh: "postgresql://user:password@localhost/dbname"
from database import engine, SessionLocal 

# Inisialisasi Faker dengan locale Indonesia
fake = Faker('id_ID')

db = SessionLocal()

# --- 1. DAFTAR USER (Sesuai Request) ---
EXISTING_USERS_DATA = [
    {14: "wahyudin"}, {15: "gustilanangp"}, {16: "sapirin"}, {17: "saphoan"}, {18: "suchie"}, 
    {19: "mjunaedi"}, {20: "winiwidiastuti"}, {21: "pepti"}, {22: "hertina"}, {23: "ikhsany"}, 
    {24: "dhewies"}, {25: "indah.fitriana"}, {26: "budiana"}, {27: "herry.irawan"}, {28: "rika.verlita"}, 
    {29: "nahryah"}, {30: "dyatmika"}, {31: "yatidar"}, {32: "cintya"}, {33: "isna_z"}, 
    {34: "cfatikhinp"}, {35: "nyomanratna"}, {36: "asukri"}, {37: "ani.rusti"}, {38: "taupik"}, 
    {39: "mfathi"}, {40: "lalu.kherli"}, {41: "siti.ms"}, {42: "eka.marwitasari"}, {43: "dita.selviana"}, 
    {44: "galina"}, {45: "pietra.wibisono"}, {46: "metaindriyana"}, {47: "desimarlian"}, {48: "roshan.fikri"}, 
    {49: "achmad.gunawan"}, {50: "rani.wandari"}, {51: "addin.khairun"}, {52: "lalu.ardani"}, {53: "desy.handayani"}, 
    {54: "aufa.praba"}, {55: "deta.novian"}, {56: "rimas"}, {57: "fanni.darmawan"}, {58: "asatriawan"}, 
    {59: "faiqs"}, {60: "hilmi.sifa"}, {61: "syafaqatul"}, {62: "ayu.rosita"}, {63: "arza"}, 
    {64: "fikri.anwar"}, {65: "salsa.nopian"}, {66: "a.felardhi"}, {67: "nursan"}, {68: "rofi.robbani"}, 
    {69: "intan.maulida"}, {70: "wardian"}, {71: "nurul.islamy"}, {72: "ayub.rahman"}, {73: "nurlailah"}, 
    {74: "rosita.fahmi"}, {75: "mhdalif.farhan"}, {76: "zammiluny"}, {77: "indrasasmita"}, {78: "andi.guslan"}, 
    {79: "wartinah"}, {80: "lalu.sudiarta"}, {81: "pande.dony"}, {82: "aris.wahyudi"}, {83: "jimanz"}, 
    {84: "linna"}, {85: "baiqyeni"}, {86: "kusmayadi-pppk"}, {87: "lastrika.muliana"}, {88: "dian.marlina"}, 
    {89: "lianurmala-pppk"}, {90: "melinda.gustina"}, {91: "wirjan"}, {92: "baiq.winda"}, {93: "rofiqo.aziza"}, 
    {94: "herisw"}, {95: "rosidi4"}, {96: "nanda.fitria"}, {97: "ana.pitriani"}, {100: "baiq.zulmeida"}, 
    {103: "najla.salshabilla"}, {104: "sahriladi-pppk"}, {105: "zamhariraula-pppk"}, {106: "musawirin-pppk"}, 
    {107: "marhamah-pppk"}, {108: "m.ahyar"}, {109: "muliasih-pppk"}, {110: "malikulmajdi-pppk"}, 
    {111: "junnaidieff-pppk"}, {112: "nasibun-pppk"}, {113: "imadeyasa-pppk"}, {114: "diahsafitri-pppk"}, 
    {115: "salamudin-pppk"}, {117: "asdasd123"}
]

# Flatten ID list untuk memudahkan pengambilan random
USER_IDS = [list(u.keys())[0] for u in EXISTING_USERS_DATA]

# --- 2. DATA PENDUKUNG (Template Kegiatan Kantor) ---
PREFIX_KEGIATAN = ["Rapat", "Koordinasi", "Supervisi", "Pengolahan Data", "Pelatihan", "Briefing", "Monitoring", "Penyusunan Laporan", "Diseminasi", "Kunjungan Lapangan"]
TOPIK_KEGIATAN = ["Sensus Ekonomi", "Susenas", "Sakernas", "Reformasi Birokrasi", "Anggaran 2025", "Statistik Pertanian", "Produk Domestik Regional Bruto", "Teknologi Informasi", "Kepegawaian", "Sistem Kearsipan"]

def get_random_activity_name():
    return f"{random.choice(PREFIX_KEGIATAN)} {random.choice(TOPIK_KEGIATAN)}"

# --- 3. GENERATE TEAMS & PROJECTS (Jika belum ada) ---
# Kita butuh Team dan Project agar kolom team_id dan project_id tidak kosong semua
def seed_teams_and_projects(user_objects):
    print("--- Seeding Teams & Projects ---")
    
    # Dummy Teams
    teams_data = ["Tim Nerwilis", "Tim IPDS", "Tim Sosial", "Tim Produksi", "Tim Distribusi", "Tim Tata Usaha"]
    teams = []
    for t_name in teams_data:
        team = Team(
            nama_tim=t_name,
            valid_from=date(2025, 1, 1),
            valid_until=date(2025, 12, 31),
            ketua_tim_id=random.choice(USER_IDS),
            warna=fake.hex_color()
        )
        teams.append(team)
    db.add_all(teams)
    db.commit()
    
    # Refresh untuk dapat ID
    for t in teams: db.refresh(t)

    # Dummy Projects
    projects_data = ["Sensus Ekonomi 2026", "Publikasi Daerah Dalam Angka", "Satu Data Indonesia", "Survei Biaya Hidup"]
    projects = []
    for p_name in projects_data:
        proj = Project(
            nama_project=p_name,
            team_id=random.choice(teams).id,
            project_leader_id=random.choice(USER_IDS)
        )
        projects.append(proj)
    db.add_all(projects)
    db.commit()
    
    # Refresh
    for p in projects: db.refresh(p)
    
    return teams, projects

# --- 4. MAIN GENERATOR ---
def generate_activities():
    print("--- Memulai Generate 1000+ Aktivitas ---")
    
    # 1. Ambil object User dari DB berdasarkan ID yang diberikan
    # Ini penting untuk relasi Many-to-Many (anggota_aktivitas_link)
    user_objects = db.query(User).filter(User.id.in_(USER_IDS)).all()
    
    if not user_objects:
        print("PERINGATAN: Tidak ada user ditemukan di database dengan ID yang diberikan.")
        print("Pastikan Anda sudah memiliki user-user tersebut di tabel 'users'.")
        return

    # 2. Buat Team dan Project dummy dulu
    teams, projects = seed_teams_and_projects(user_objects)

    activities = []
    
    for i in range(1050): # Generate 1050 untuk cadangan
        # Tentukan Tanggal di 2025
        start_date = fake.date_between(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
        
        # Durasi kegiatan (1 hari s/d 5 hari)
        duration = random.randint(0, 5) 
        end_date = start_date + timedelta(days=duration)
        
        # Jam
        h_start = random.randint(8, 14)
        jam_mulai = time(h_start, 0)
        jam_selesai = time(h_start + random.randint(1, 4), 0)

        # Randomly assign Project or None
        assigned_project = random.choice(projects + [None, None]) # 50% chance None
        assigned_project_id = assigned_project.id if assigned_project else None
        
        # Randomly assign Team
        assigned_team = random.choice(teams)
        
        creator_id = random.choice(USER_IDS)

        act = Aktivitas(
            nama_aktivitas=get_random_activity_name(),
            deskripsi=fake.paragraph(nb_sentences=3),
            tanggal_mulai=start_date,
            tanggal_selesai=end_date,
            jam_mulai=jam_mulai,
            jam_selesai=jam_selesai,
            creator_user_id=creator_id,
            team_id=assigned_team.id,
            project_id=assigned_project_id,
            melibatkan_kepala=random.choice([True, False, False]), # Lebih banyak False
            # public_id biasanya digenerate otomatis oleh DB (gen_random_uuid), 
            # tapi jika error not-null di python level, bisa pakai uuid.uuid4()
        )

        # -- Menambahkan Peserta (Anggota Aktivitas) --
        # Ambil 2 sampai 10 orang peserta secara acak dari user_objects
        peserta = random.sample(user_objects, k=random.randint(2, 10))
        
        # SQLAlchemy magic: tambahkan ke relationship 'users'
        # Pastikan di models.py relasi 'users' didefinisikan dengan benar
        for p in peserta:
            act.users.append(p)
            
        activities.append(act)

        # Commit per 100 data agar tidak terlalu berat memori
        if len(activities) >= 100:
            db.add_all(activities)
            db.commit()
            activities = []
            print(f"Generated {i+1} aktivitas...")

    # Commit sisa data
    if activities:
        db.add_all(activities)
        db.commit()
        print("Sisa aktivitas berhasil disimpan.")

    print("--- SELESAI ---")

if __name__ == "__main__":
    generate_activities()