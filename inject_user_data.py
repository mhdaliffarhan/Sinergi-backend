import sys
import os
from typing import Optional

# Menambahkan path saat ini agar bisa impor 'models', 'database', dan 'security'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import models
    import database
    import security  # <-- Kita butuh ini untuk hashing password
    from sqlalchemy.orm import Session
except ImportError as e:
    print(f"Error: Gagal mengimpor modul. Pastikan skrip ini ada di folder yang sama dengan main.py.")
    print(f"Detail: {e}")
    sys.exit(1)

# --- DATA BLOB BARU ANDA (DENGAN JK) ---
DATA_BLOB = """
Username	NIP BPS	NIP	Nama	NoHp	JK
wahyudin	340012842	196612311991031140	Dr.Drs. Wahyudin, M.M	+62 812-3690-1184	LK
gustilanangp	340013471	196808171992121001	Ir. I Gusti Lanang Putra	+62 812-4635-9129	LK
sapirin	340014303	196612311994011002	Drs. Sapirin	+62 813-5342-5120	LK
saphoan	340014444	196712311994011001	Drs. Muhamad Saphoan	+62 812-4626-0450	LK
suchie	340017018	198008272003122003	Suci Purnamawati, S.ST, MM	+62 878-1002-2048	PR
mjunaedi	340015139	197206211995121001	Dr. Mohammad Junaedi, S.Si., M.T	+62 813-6131-2116	LK
winiwidiastuti	340016544	198104212002122004	Wini Widiastuti, S.ST, M.Sc	+62 812-9367-2304	PR
pepti	340050195	198602062009022005	Pepti Maya Puspita, SST, M.Ec.Dev	+62 818-864-400	PR
hertina	340017065	198110192003122002	Hertina Yusnissa, SST, MM	+62 823-3976-7867	PR
ikhsany	340017056	198105142003121003	M. Ikhsany Rusyda, SST., M.Si	+62 818-0360-7892	LK
dhewies	340015173	197505041995122001	Dewi Sri Wijihayati, S.Si., MSE	+62 821-3860-6329	PR
indah.fitriana	340019263	198401202007012003	Indah Fitriana, SST	+62 819-0923-0219	PR
budiana	340019267	198304032007011007	I Nyoman Budiana, SST	+62 819-1756-1483	LK
herry.irawan	340017711	198506012005021002	Herry Irawan, SE, M.Ak	+62 878-6512-1185	LK
rika.verlita	340020172	198508012008012005	Rika Verlita, SST	+62 821-9925-0348	PR
nahryah	340050061	198504202009022008	Dian Nahryah, SST	+62 812-3630-2902	PR
dyatmika	340017401	198203192004121002	I Putu Dyatmika, SST	+62 812-3780-2900	LK
yatidar	340050272	198610232009022006	Yati Daryati Nurmalasari, SST	+62 819-3073-6129	PR
cintya	340053292	198708272009122004	Cintya Pratiwi Paramitha, S.ST., M.M.	+62 818-0808-6233	PR
isna_z	340053294	198707242009122006	Isna Zuriatina, SST., MT.	+62 818-0369-0835	PR
cfatikhinp	340054217	198708152010121005	Chairul Fatikhin Putra, SST, M.M.	+62 878-8170-6407	LK
nyomanratna	340054218	198808312010122002	Ni Nyoman Ratna Puspitasari, SST	+62 818-0796-6160	PR
asukri	340016866	197804152002121006	Ahmad Sukri, S.Kom	+62 819-1704-6516	LK
ani.rusti	340055731	198711222012112001	Ani Rustiani, SST	+62 852-2475-2476	PR
taupik	340055933	198904292012111001	Taupikurrahman, SST, M.Si	+62 821-4596-2576	LK
mfathi	340055846	198808242012111001	Muhammad Fathi, SST, M.T.I.	+62 819-1592-3470	LK
lalu.kherli	340016051	197903011999121001	Lalu Kherli Kusnendar, SST	+62 818-0363-5379	LK
siti.ms	340018186	198301032006042002	Siti Mar'atus Sa'adah, SE, M.Ak	+62 817-5710-332	PR
eka.marwitasari	340017714	198503132005022001	Eka Marwitasari, SST	+62 878-8327-8886	PR
dita.selviana	340020298	198809012008012002	Dita Selviana Faradilla, SST	+62 878-4604-1684	PR
galina	340020448	198703012008012002	Galina Margayana, SE	+62 813-6730-4869	PR
pietra.wibisono	340055183	198312212011011005	Pietra Rezana Wibisono, S.P.	+62 852-3936-3906	LK
metaindriyana	340055838	198905292012112001	Meta Indriyana, SST	+62 878-8832-4929	PR
desimarlian	340055753	198812252012112001	Desi Marliannisa, SST	+62 819-0513-2693	PR
roshan.fikri	340020300	198801032008011004	Roshan Fikri, SST	+62 818-0375-1158	LK
achmad.gunawan	340055170	198107242011011011	Achmad Gunawan, S.Adm	+62 819-1794-5159	LK
rani.wandari	340059722	199805292019122001	Rani Wandari, S.Tr.Stat.	+62 813-3988-9630	PR
addin.khairun	340058106	199410242018021001	Addin Khairun Dwin, SST	+62 819-3313-4643	LK
lalu.ardani	340059598	199509092019121001	Lalu Ardani Aulia, S.Tr.Stat.	+62 877-1656-3349	LK
desy.handayani	340059471	199612212019122002	Desy Handayani, S.Tr.Stat.	+62 831-2961-8331	PR
aufa.praba	340059220	199611292019031001	Aufa Praba Raditya, S.Stat.	+62 813-3988-9717	LK
deta.novian	340058202	199611142018022001	Deta Novian Ariesandy, SST	+62 853-3996-6930	PR
rimas	340058948	199508102019012001	Rimassatya Pawestri, S.Tr.Stat.	+62 852-5996-0795	PR
fanni.darmawan	340057726	199504132017011002	Fanni Budi Darmawan, SST	+62 877-6653-4224	LK
asatriawan	340056747	199104132014101001	Ari Satriawan, SST	+62 812-1996-3606	LK
faiqs	340058817	199606252019011002	M Faiq Syafiqi Awwali Manshur, S.Tr.Stat.	+62 813-1040-8485	LK
hilmi.sifa	340058765	199606142019012003	Hilmi Sifa' Iftitah, S.Tr.Stat.	+62 823-3258-4822	PR
syafaqatul	340057608	199305252016022001	Syafaqatul Humairoh, SST	+62 812-3975-6307	PR
ayu.rosita	340057313	199403062016022001	Ayu Rosita Sari, SST	+62 819-1733-0372	PR
arza	340058624	199603182019011001	Arza Habibul Asdid, S.Tr.Stat.	+62 819-3822-7533	LK
fikri.anwar	340057494	199210192016021001	Muhamad Fikri Anwar, SST	+62 878-8218-6851	LK
salsa.nopian	340057584	199211042016021001	Salsa Nopian Pamungkas, SST	+62 813-6666-4696	LK
a.felardhi	340059373	199712252019121002	Adlan Felardhi, S.Tr.Stat.	+62 831-2900-9392	LK
nursan	340019680	198301212007011001	Muhamad Nursan, S.Adm	+62 878-6164-2019	LK
rofi.robbani	340060467	199907082022011005	Abdurrofi Robbani, S.Tr.Stat.	+62 821-1382-0297	LK
intan.maulida	340060691	199906272022012003	Intan Maulida Khoirun Nisa', S.Tr.Stat.	+62 857-9167-7389	PR
wardian	340019265	198405172007011003	Amy Wardian Pratama, SST., M.E.	+62 813-3962-2231	LK
nurul.islamy	340057173	199105232014121001	Nurul Islamy, SST	+62 811-390-104	LK
ayub.rahman	340057725	199612092017011001	Ayub Abdul Rahman, SST	+62 819-1804-8196	LK
nurlailah	340012575	196904141990032001	Nurlailah	+62 819-0790-2151	PR
rosita.fahmi	340017228	198405212003122001	Rosita Fahmi	+62 853-3815-8257	PR
mhdalif.farhan	340063283	200205222024121007	M. Alif Farhan, S.Tr.Stat	+62 895-6025-88736	LK
zammiluny	340016137	197812202000121002	Akhmad Zammiluny, MM	+62 812-3707-939	LK
indrasasmita	340050125	198509202009021010	Indra Sasmita Utama, SST	+62 818-0810-8407	LK
andi.guslan	340014027	197510141994011001	Andi Guslan, SE	+62 817-5790-475	LK
wartinah	340016161	197911112000122002	Wartinah, SST	+62 819-1684-7391	PR
lalu.sudiarta	340052171	198107272009011010	Lalu Sudiarta Utama, S. Adm	+62 817-5700-665	LK
pande.dony	340056543	199107192014031002	Pande Gde Dony Gumilar, S.Si, M.M.	+62 812-3964-9003	LK
aris.wahyudi	340016404	198204182001121004	Aris Wahyudi, S.P, M.Ak	+62 818-0367-1759	LK
jimanz	340020473	198008072007101001	Sujiman, SE	+62 819-0755-8477	LK
linna	340055178	199002052011012003	Linna Winarni, S.M.	+62 878-6536-5646	PR
baiqyeni	340018187	198612312006042001	Baiq Yeni Sulistiana, S.Adm, M.Ak	+62 878-6446-5030	PR
kusmayadi-pppk	340062283	197912312023211022	Kusmayadi, S.I.Kom	+62 817-5750-879	LK
lastrika.muliana	340061384	198804162022032004	Lastrika Muliana, S.E.	+62 852-9205-5456	PR
dian.marlina	340017718	198407202005022001	Dian Marlina, S.A.P.	+62 819-0785-6420	PR
lianurmala-pppk	340062870	199207152024212008	Marlia Nurmala, A.Md.	+62 819-1703-7011	PR
melinda.gustina	340061096	200008282022012002	Kadek Melinda Gustina Hari, A.Md.Kb.N.	+62 821-4576-9867	PR
wirjan	340012203	196812311989031013	I Wayan Wirjan, SE	+62 819-3315-5430	LK
baiq.winda	340063705	199310092025062002	Baiq Winda Widiyastari, S.H.	+62 852-0522-3738	PR
rofiqo.aziza	340063932	200102172025062008	Rofiqo Azizaturrahmi, S.Psi.	+62 859-3454-4673	PR
herisw	340056628	197312252014061001	Heri Suria Wirawan		LK
rosidi4	340019393	197512312007011009	Rosidi	+62 818-0379-6150	LK
nanda.fitria	340063875	199801272025062006	Nanda Fitria Therina Midy, A.Md.	+62 895-4223-98699	PR
ana.pitriani	340063677	199801102025062005	Ana Pitriani, A.Md.	+62 819-9996-8861	PR
sahriladi-pppk	340065584	199906112025211019	Sahril Adikusuma	+62 878-7334-5376	LK
zamhariraula-pppk	340066021	199109042025211029	Zamharir Aula S.Pd.I	+62 819-1821-7082	LK
musawirin-pppk	340065254	199205012025211048	Musawirin	+62 817-7573-1736	LK
marhamah-pppk	340065052	198504112025212035	Marhamah	+62 878-6578-6759	PR
m.ahyar	340013473	196612311992121001	Ir. Muhammad Ahyar 	+62 878-6683-2022	LK
muliasih-pppk	340065239	198302102025212046	Muliasih	+62 853-3866-6261	PR
malikulmajdi-pppk	340065038	199406172025211052	Malikul Majdi  	+62 877-0111-4555	LK
junnaidieff-pppk	340064938	198406122025211065	Junnaidi Effendi	+62 831-2947-4373	LK
nasibun-pppk	340065276	197212312025211124	Nasibun	+62 819-1776-7089	LK
imadeyasa-pppk	340064775	199509212025211031	I Made Suparta Yasa  		LK
diahsafitri-pppk	340064443	200009122025212024	Diah Puspita Safitri S.M.		PR
baiq.zulmeida	340057010	199205082014122001	Baiq Try Zulmeida SST, M.Ec	+62 819-1832-0416	PR
salamudin-pppk	340065600	197907232025211025	 Salamudin S.E.		LK
"""

def format_phone_number(nohp: str) -> Optional[str]:
    """
    Membersihkan dan memformat nomor HP ke format '62...'.
    Mengembalikan None jika input kosong atau tidak valid.
    """
    if not nohp:
        return None
    
    # Hapus semua karakter non-numerik (termasuk spasi, +, -)
    nohp_numeric = "".join(filter(str.isdigit, nohp.strip()))
    
    # Kasus: +62 812... (sudah di-handle oleh filter isdigit, tapi kita jaga-jaga)
    if nohp.strip().startswith('+62'):
        nohp_numeric = nohp_numeric[2:] # Hapus 62 di awal
        return f"62{nohp_numeric}" # Tambahkan 62 kembali

    # Kasus: 08...
    if nohp_numeric.startswith('08'):
        return '62' + nohp_numeric[1:]
    
    # Kasus: 628...
    if nohp_numeric.startswith('628'):
        return nohp_numeric
    
    # Kasus: 8... (tanpa 0 di depan)
    if nohp_numeric.startswith('8'):
        return '62' + nohp_numeric
    
    # Jika format lain, anggap tidak valid
    print(f"Format NoHp tidak dikenali: {nohp}")
    return None

def get_jk_full(jk_short: str) -> Optional[str]:
    """Mengubah LK menjadi Laki-laki dan PR menjadi Perempuan."""
    if not jk_short:
        return None
    jk_upper = jk_short.strip().upper()
    if jk_upper == 'LK':
        return 'Laki-laki'
    if jk_upper == 'PR':
        return 'Perempuan'
    return None

def main_inject():
    """
    Fungsi utama untuk injeksi data.
    """
    # Dapatkan sesi database
    db = database.SessionLocal()
    
    lines = DATA_BLOB.strip().split('\n')
    header_line = lines[0]
    rows = lines[1:]
    
    # Validasi header (pastikan header_line tidak kosong dan punya '\t')
    if not header_line or '\t' not in header_line:
        print(f"Error: Format header tidak valid. Ditemukan: {header_line}")
        db.close()
        return

    header = header_line.split('\t')
    print(f"Header terdeteksi: {header}")
    
    updated_count = 0
    created_count = 0
    
    print("Memulai proses injeksi data pengguna...")
    
    try:
        for index, line in enumerate(rows):
            if not line.strip():
                continue # Lewati baris kosong
                
            parts = line.split('\t')
            
            # Pastikan jumlah kolom sesuai
            if len(parts) < len(header):
                print(f"Peringatan: Baris {index+2} dilewati (data tidak lengkap). Isi: {line}")
                continue
            
            # Buat kamus data
            data = dict(zip(header, parts))
            
            # Ambil data dari kamus
            username = data.get('Username').strip()
            nip = data.get('NIP').strip() or None
            nip_bps = data.get('NIP BPS').strip() or None
            nama_raw = data.get('Nama').strip() or None
            nohp_raw = data.get('NoHp').strip() or None
            jk_raw = data.get('JK').strip() or None
            
            # Bersihkan nama dari spasi berlebih di akhir (seperti "Malikul Majdi  ")
            nama = " ".join(nama_raw.split()) if nama_raw else None

            if not username:
                print(f"Peringatan: Baris {index+2} dilewati (username kosong).")
                continue

            # Format NoHp dan JK
            formatted_nohp = format_phone_number(nohp_raw)
            formatted_jk = get_jk_full(jk_raw)

            # Cari user di database
            user = db.query(models.User).filter(models.User.username == username).first()
            
            if user:
                # --- UPDATE PENGGUNA YANG ADA ---
                print(f"FOUND: {username}. Memperbarui data...")
                user.nip = nip
                user.nipbps = nip_bps
                user.nohp = formatted_nohp
                user.jenis_kelamin = formatted_jk
                # (Opsional) Update nama jika ada perbedaan
                if nama and user.nama_lengkap != nama:
                    print(f"  -> Mengubah nama dari '{user.nama_lengkap}' menjadi '{nama}'")
                    user.nama_lengkap = nama
                
                updated_count += 1
            else:
                # --- BUAT PENGGUNA BARU ---
                print(f"NOT FOUND: {username}. Membuat user baru...")
                
                # Hash password default
                hashed_password = security.get_password_hash("password123")
                
                new_user = models.User(
                    username=username,
                    hashed_password=hashed_password,
                    nama_lengkap=nama,
                    sistem_role_id=3,  # Default Sesuai permintaan
                    jabatan_id=2,      # Default Sesuai permintaan
                    nip=nip,
                    nipbps=nip_bps,
                    nohp=formatted_nohp,
                    jenis_kelamin=formatted_jk,
                    is_active=True # Asumsi user baru langsung aktif
                )
                db.add(new_user)
                created_count += 1
        
        # Commit semua perubahan ke database
        db.commit()
        
        print("\n" + "="*30)
        print("PROSES INJEKSI SELESAI")
        print("="*30)
        print(f"✅ Berhasil memperbarui {updated_count} pengguna.")
        print(f"✨ Berhasil membuat {created_count} pengguna baru.")
        
    except Exception as e:
        db.rollback()
        print(f"\n" + "!"*30)
        print(f"TERJADI ERROR FATAL: {e}")
        print("!"*30)
        print("Semua perubahan telah dibatalkan (rollback). Tidak ada data yang disimpan.")
    finally:
        db.close()
        print("Koneksi database ditutup.")

# Ini adalah 'entry point' jika skrip dijalankan langsung
if __name__ == "__main__":
    
    # Kita perlu memastikan 'database.py' sudah menginisialisasi engine
    try:
        if not hasattr(database, 'engine'):
             print("Inisialisasi engine database...")
             pass
        
        print(f"Menggunakan database: {database.engine.url}")
    except Exception as e:
        print(f"Gagal menginisialisasi database: {e}")
        sys.exit(1)
        
    main_inject()