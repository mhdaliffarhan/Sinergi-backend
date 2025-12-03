import httpx
from typing import Optional

# --- KONFIGURASI  ---
WA_URL = "http://36.95.114.173:5252"
WA_USER = "bps52000"
WA_PASS = "ntb52"
# ---------------------------------------------

def format_phone_number(nohp: str) -> Optional[str]:
    """
    Memformat nomor HP dari '08...' atau '62...' menjadi '628..._@s.whatsapp.net'.
    Mengembalikan None jika format tidak valid.
    """
    if not nohp:
        return None
    
    # Hapus karakter non-digit
    nohp_numeric = "".join(filter(str.isdigit, nohp))
    
    if nohp_numeric.startswith('08'):
        # Ganti '08' di awal dengan '628'
        nohp_formatted = '62' + nohp_numeric[1:]
    elif nohp_numeric.startswith('62'):
        nohp_formatted = nohp_numeric
    else:
        return None
        
    return f"{nohp_formatted}@s.whatsapp.net"

async def send_whatsapp_message(phone_number: str, message: str):
    """
    Mengirim pesan WhatsApp.
    PENTING: Fungsi ini sekarang me-raise Exception jika gagal, 
    agar ditangkap oleh cron job sebagai status 'failed'.
    """
    # 1. Validasi Kredensial
    if not WA_URL or not WA_USER or not WA_PASS:
        raise Exception("Konfigurasi WA (URL/User/Pass) belum lengkap.")

    # 2. Validasi Nomor HP
    formatted_phone = format_phone_number(phone_number)
    if not formatted_phone:
        # Raise error agar status di DB jadi 'failed' dan tidak dicoba ulang terus menerus
        raise Exception(f"Format nomor HP tidak valid: {phone_number}")

    payload = {
        "phone": formatted_phone,
        "message": message
    }
    
    # Basic Auth
    auth = (WA_USER, WA_PASS)
    
    # 3. Kirim Request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{WA_URL}/send/message", 
                json=payload, 
                auth=auth,
                timeout=30.0 # Timeout diperpanjang sedikit agar aman
            )
            
            # 4. Cek HTTP Status Code
            if response.status_code == 200:
                # Cek isi JSON, kadang server return 200 tapi isinya error logic
                resp_json = response.json()
                
                # Asumsi jika API mengembalikan field 'status': false atau 'error'
                # Sesuaikan logika ini dengan respon asli gateway Anda jika perlu
                if isinstance(resp_json, dict) and resp_json.get("status") is False:
                     raise Exception(f"Gateway Logic Error: {resp_json}")
                
                print(f"WA Sukses ke: {formatted_phone}")
                return True, resp_json
            
            elif response.status_code == 401:
                raise Exception("WA Unauthorized (401): Sesi mati atau password salah. Cek koneksi QR.")
            
            else:
                raise Exception(f"HTTP Error {response.status_code}: {response.text}")
                
        except httpx.RequestError as e:
            # Error koneksi (timeout, dns, dll)
            raise Exception(f"Koneksi ke WA Gateway gagal: {e}")
        except Exception as e:
            # Error lainnya
            raise e