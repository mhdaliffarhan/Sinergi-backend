import httpx
from typing import Optional

# --- PERBAIKAN DI SINI ---
# Kredensial sekarang di-hardcode sesuai permintaan
WA_URL = "http://36.95.114.173:5252"
WA_USER = "bps52000"
WA_PASS = "ntb52"
# --- AKHIR PERBAIKAN ---

def format_phone_number(nohp: str) -> Optional[str]:
    """
    Memformat nomor HP dari '08...' atau '62...' menjadi '628..._@s.whatsapp.net'.
    Mengembalikan None jika format tidak valid.
    """
    if not nohp:
        return None
    
    nohp_numeric = "".join(filter(str.isdigit, nohp))
    
    if nohp_numeric.startswith('08'):
        # Ganti '08' di awal dengan '628'
        nohp_formatted = '62' + nohp_numeric[1:]
    elif nohp_numeric.startswith('62'):
        # Sudah benar
        nohp_formatted = nohp_numeric
    else:
        # Format tidak dikenali, jangan kirim
        print(f"Peringatan WA: Format nomor tidak valid: {nohp}")
        return None
        
    return f"{nohp_formatted}@s.whatsapp.net"

async def send_whatsapp_message(phone_number: str, message: str):
    """
    Mengirim pesan WhatsApp secara asynchronous.
    Selalu mengembalikan tuple (bool, response_message)
    """
    if not WA_URL or not WA_USER or not WA_PASS:
        # (Pemeriksaan ini sekarang seharusnya selalu lolos, tapi kita biarkan untuk keamanan)
        msg = "PERINGATAN: Kredensial API WhatsApp tidak di-set di services_wa.py."
        print(msg)
        return False, {"error": msg}

    formatted_phone = format_phone_number(phone_number)
    if not formatted_phone:
        msg = f"Peringatan WA: Format nomor salah {phone_number}"
        print(msg)
        return False, {"error": msg}

    payload = {
        "phone": formatted_phone,
        "message": message
    }
    
    # Ini adalah implementasi dari 'Basic Auth' yang Anda sebutkan.
    # httpx akan otomatis meng-encode 'username:password' ke Base64.
    auth = (WA_USER, WA_PASS)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{WA_URL}/send/message", 
                json=payload, 
                auth=auth,
                timeout=10.0
            )
            
            if response.status_code == 200:
                print(f"Notifikasi WA BERHASIL dikirim ke {formatted_phone}")
                return True, response.json()
            else:
                error_msg = f"ERROR Gagal mengirim WA ke {formatted_phone}: {response.status_code} - {response.text}"
                print(error_msg)
                try:
                    return False, response.json()
                except Exception:
                    return False, {"error": error_msg}
                
        except httpx.RequestError as e:
            error_msg = f"ERROR Exception saat mengirim WA: {e}"
            print(error_msg)
            return False, {"error": error_msg}