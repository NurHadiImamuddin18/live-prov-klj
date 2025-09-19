# main.py
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import telebot
import pymysql
import gspread
import json
from google.oauth2.service_account import Credentials
# setup logging
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env
load_dotenv()

# Ambil GOOGLE_CREDS_JSON
creds_json = os.getenv("GOOGLE_CREDS_JSON")
if not creds_json:
    raise ValueError("Environment variable GOOGLE_CREDS_JSON belum diset!")

# Debug awal (cek 200 karakter pertama)
print("==== DEBUG GOOGLE_CREDS_JSON ====")
print(repr(creds_json))
print("===============================")

# Parse ke dictionary langsung (tidak replace apapun)
creds_dict = json.loads(creds_json)

# Buat credentials
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
gc = gspread.authorize(creds)

# Buka Google Sheet
try:
    sh = gc.open_by_key("1-pclr-o0mbvyH8XFtOlmScgeEtTnQyq4S8wdbX6XmgI")
    worksheet = sh.sheet1
    logger.info("Google Sheet siap!")
except Exception as e:
    logger.exception("Gagal membuka Google Sheet")
    worksheet = None

    # load env
load_dotenv()

TOKEN = os.getenv("TOKEN")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "telegram_files")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)
UPLOAD_DIR_FOTO = "upload"   # folder untuk foto
os.makedirs(UPLOAD_DIR_FOTO, exist_ok=True)

# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# DB helper
def get_db_conn():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def save_file_metadata(meta):
    sql = """
    INSERT INTO files
    (telegram_file_id, original_filename, uploader_username)
    VALUES (%s,%s,%s)
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                meta.get("telegram_file_id"),
                meta.get("original_filename"),
                meta.get("uploader_username")
            ))
    finally:
        conn.close()

# helpers untuk buat nama file unik
def make_stored_filename(original_filename, file_unique_id):
    ext = ""
    if "." in original_filename:
        ext = original_filename.split(".")[-1]
    # gunakan timestamp + file_unique_id untuk unik
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    if ext:
        return f"{ts}_{file_unique_id}.{ext}"
    else:
        return f"{ts}_{file_unique_id}"

# Handler: start
@bot.message_handler(commands=["start"])
def cmd_start(msg):
    bot.reply_to(msg, "Selamat pagi!💪 Semangat menyelesaikan tugas hari ini! 🚀\n"
                      "Kirim /help untuk melihat format yang tersedia ."
                 )


@bot.message_handler(commands=["help"])
def cmd_help(msg):
    template_order = (
        "/ORDER :\n"
        "NO SC : \n"
        "NO INTERNET :  \n"
        "NO VOIP : -\n"
        "NCLI : -\n"
        "NAMA PELANGGAN : \n"
        "ALAMAT : \n"
        "CP PELANGGAN : \n"
        "STO : \n"
        "MITRA : \n"
        "ODP REAL : \n"
        "PORT : \n"
        "MARKING DC AWAL : \n"
        "MARKING DC AKHIR : \n"
        "AC-OF-SM-1B : \n"
        "AC-OF-SM-1-3SL : \n"
        "CLAMP-HOOK : \n"
        "OTP-FTTH-1 : \n"
        "PREKSO-INTRA-15-RS : -\n"
        "PREKSO-INTRA-20-RS : \n"
        "RS-IN-SC-1 : \n"
        "S-CLAMP-SPRINER : \n"
        "SOC-ILS : \n"
        "SOC-SUM : \n"
        "QRCODE : \n"
        "SN ONT : \n"
        "STBID : \n"
        "TAG ODP : \n"
        "TAG PELANGGAN : \n"
        "LABOR : \n"
        "VALINS ID : \n"
        "SLOT : \n"
        "PORT : \n"
        "IP OLT : \n"
        "HASIL VALINS : \n"
        "ONU GENDONG : \n\n"
        "⚠️ Catatan: Jika data tidak ada, bisa diisi dengan (-) dan data harus sesuai dengan format yang telah di tentukan"
    )

    bot.reply_to(msg, template_order)

# Handler: menerima text atau caption dari photo
@bot.message_handler(content_types=["text", "photo"])
def handle_order_text(msg):
    # Ambil text: dari caption kalau photo, atau msg.text kalau text biasa
    if msg.content_type == "photo":
        text = msg.caption.strip() if msg.caption else ""
    else:
        text = msg.text.strip() if msg.text else ""

    # Cek prefix "/ORDER:"
    if not text.startswith("/ORDER:"):
        return  # Bukan order, abaikan handler ini

    try:
        # Parsing data
        data = {}
        port_count = 0
        for line in text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                if key.startswith("/"):
                    key = key[1:]  # hapus '/'

                # khusus PORT kedua
                if key.upper() == "PORT":
                    port_count += 1
                    if port_count == 2:
                        key = "PORTT"

                data[key] = value.strip()

        # List field wajib
        required_fields = [
            "ORDER", "NO SC", "NO INTERNET", "NAMA PELANGGAN", "ALAMAT", "CP PELANGGAN"
        ]

        # Cek field wajib yang hilang atau kosong
        missing_fields = [field for field in required_fields if field not in data or not data[field]]

        if missing_fields:
            bot.reply_to(
                msg,
                "❌ Format order tidak sesuai!\n"
                "Field berikut hilang atau kosong:\n- " + "\n- ".join(missing_fields)
            )
            return

        # Set default "-" untuk field lain yang tidak wajib
        defaults = [
            "NO VOIP", "NCLI", "STO", "MITRA", "ODP REAL", "PORT", "MARKING DC AWAL",
            "MARKING DC AKHIR", "AC-OF-SM-1B", "AC-OF-SM-1-3SL", "CLAMP-HOOK",
            "OTP-FTTH-1", "PREKSO-INTRA-15-RS", "PREKSO-INTRA-20-RS", "RS-IN-SC-1",
            "S-CLAMP-SPRINER", "SOC-ILS", "SOC-SUM", "QRCODE", "SN ONT (TYPE)",
            "STBID (TYPE)", "TAG ODP", "TAG PELANGGAN", "LABOR", "VALINS ID",
            "SLOT", "PORTT", "IP OLT", "HASIL VALINS", "ONU GENDONG"
        ]
        for field in defaults:
            if field not in data or not data[field]:
                data[field] = "-"

        # Tambahkan sender
        data["SENDER"] = getattr(msg.from_user, "username", "-")

        # Simpan ke database
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO orders (
                    order_type, no_sc, no_internet, no_voip, ncli, nama_pelanggan,
                    alamat, cp_pelanggan, sto, mitra, odp_real, port, marking_dc_awal,
                    marking_dc_akhir, ac_of_sm_1b, ac_of_sm_1_3sl, clamp_hook,
                    otp_ftth_1, prekso_intra_15_rs, prekso_intra_20_rs, rs_in_sc_1,
                    s_clamp_sprinter, soc_ils, soc_sum, qrcode, sn_ont_type, stb_id_type,
                    tag_odp, tag_pelanggan, labor, valins_id, slot, portt, ip_olt, hasil_valins,
                    onu_gendong, sender_username
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """
                cursor.execute(sql, (
                    data.get("ORDER"), data.get("NO SC"), data.get("NO INTERNET"),
                    data.get("NO VOIP"), data.get("NCLI"), data.get("NAMA PELANGGAN"),
                    data.get("ALAMAT"), data.get("CP PELANGGAN"), data.get("STO"),
                    data.get("MITRA"), data.get("ODP REAL"), data.get("PORT"),
                    data.get("MARKING DC AWAL"), data.get("MARKING DC AKHIR"),
                    data.get("AC-OF-SM-1B"), data.get("AC-OF-SM-1-3SL"),
                    data.get("CLAMP-HOOK"), data.get("OTP-FTTH-1"),
                    data.get("PREKSO-INTRA-15-RS"), data.get("PREKSO-INTRA-20-RS"),
                    data.get("RS-IN-SC-1"), data.get("S-CLAMP-SPRINER"), data.get("SOC-ILS"),
                    data.get("SOC-SUM"), data.get("QRCODE"), data.get("SN ONT (TYPE)"),
                    data.get("STBID (TYPE)"), data.get("TAG ODP"), data.get("TAG PELANGGAN"),
                    data.get("LABOR"), data.get("VALINS ID"), data.get("SLOT"), data.get("PORTT"), data.get("IP OLT"),
                    data.get("HASIL VALINS"), data.get("ONU GENDONG"),
                    data.get("SENDER")
                ))
                conn.commit()
        finally:
            conn.close()

        # Kirim ke Google Sheets
        send_order_to_sheet(data)

        bot.reply_to(msg, "✅ Data berhasil disimpan, Terimakasih")
    except Exception as e:
        logger.exception("Error saat menyimpan order")
        bot.reply_to(msg, "❌ Terjadi kesalahan saat menyimpan order.")


def send_order_to_sheet(data):
    if not worksheet:
        logger.warning("Worksheet belum siap")
        return

    # Susun data sesuai urutan kolom
    columns = [
        "ORDER","NO SC","NO INTERNET","NO VOIP","NCLI","NAMA PELANGGAN",
        "ALAMAT","CP PELANGGAN","STO","MITRA","ODP REAL","PORT",
        "MARKING DC AWAL","MARKING DC AKHIR","AC-OF-SM-1B","AC-OF-SM-1-3SL",
        "CLAMP-HOOK","OTP-FTTH-1","PREKSO-INTRA-15-RS","PREKSO-INTRA-20-RS",
        "RS-IN-SC-1","S-CLAMP-SPRINER","SOC-ILS","SOC-SUM","QRCODE",
        "SN ONT (TYPE)","STBID (TYPE)","TAG ODP","TAG PELANGGAN","LABOR",
        "VALINS ID","SLOT", "PORTT", "IP OLT","HASIL VALINS","ONU GENDONG","SENDER"
    ]

    row = [data.get(col, "-") for col in columns]

    try:
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Order berhasil dikirim ke Google Sheets")
    except Exception as e:
        logger.exception("Gagal mengirim order ke Google Sheets")



# Handler: menerima document (file seperti pdf/docx)
# Handler: menerima document (file seperti pdf/docx/xlsx)
@bot.message_handler(content_types=["document"])
def handle_document(msg):
    doc = msg.document
    file_id = doc.file_id
    original_name = doc.file_name or "unknown"
    mime_type = doc.mime_type or ""
    file_size = doc.file_size or 0
    caption = msg.caption or ""

    try:
        # Ambil file dari Telegram
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)

        # Simpan dengan nama asli persis
        stored_filename = original_name
        stored_path = os.path.join(UPLOAD_DIR, stored_filename)

        with open(stored_path, "wb") as f:
            f.write(downloaded)

        # Simpan metadata ke DB
        meta = {
            "telegram_file_id": file_id,
            "original_filename": original_name,
            "uploader_username": getattr(msg.from_user, "username", None),
        }
        save_file_metadata(meta)

        # Bedakan pesan berdasarkan ekstensi
        ext = original_name.split(".")[-1].lower()
        if ext in ["pdf", "doc", "docx", "xls", "xlsx"]:
            jenis = "Dokumen"
        elif ext in ["jpg", "jpeg", "png"]:
            jenis = "Gambar"
        else:
            jenis = "File"

        bot.reply_to(
            msg,
            f"{jenis} berhasil disimpan ✅\n"
            # f"Nama asli: `{original_name}`\n"
            # f"Disimpan sebagai: "
        )
    except Exception as e:
        logger.exception("Error saat menerima document")
        bot.reply_to(msg, "Maaf, terjadi kesalahan saat menyimpan file.")

@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    photos = msg.photo
    photo = photos[-1]
    file_id = photo.file_id
    file_unique_id = photo.file_unique_id
    original_name = f"photo_{file_unique_id}.jpg"

    try:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)

        stored_filename = f"{file_unique_id}.jpg"
        stored_path = os.path.join(UPLOAD_DIR_FOTO, stored_filename)
        with open(stored_path, "wb") as f:
            f.write(downloaded)

        # Simpan metadata ke DB
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                sql = "INSERT INTO foto (foto_id, foto_name) VALUES (%s, %s)"
                cursor.execute(sql, (file_unique_id, stored_filename))
        finally:
            conn.close()

    except Exception as e:
        logger.exception("Error saat menerima photo")  # perbaikan typo
        bot.reply_to(msg, "Gagal mengunduh foto, silakan coba lagi.")



if __name__ == "__main__":
    print("Bot running...")
    bot.infinity_polling(timeout=60, long_polling_timeout = 60)
