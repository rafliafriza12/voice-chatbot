import os
from google import genai
from google.genai import types
from pydantic import TypeAdapter
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-2.0-flash"

# TODO: Ambil API key dari file .env
# Gunakan os.getenv("NAMA_ENV_VARIABLE") untuk mengambil API Key dari file .env.
# Pastikan di file .env terdapat baris: GEMINI_API_KEY=your_api_key
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")

# Prompt sistem yang digunakan untuk membimbing gaya respons LLM
system_instruction = """
You are a responsive, intelligent, and fluent virtual assistant who communicates in Indonesian.
Your task is to provide clear, concise, and informative answers in response to user queries or statements spoken through voice.

Your answers must:
- Be written in polite and easily understandable Indonesian.
- Be short and to the point (maximum 2–3 sentences).
- Avoid repeating the user's question; respond directly with the answer.
- Avoid answering with numbers, if the answer contains numbers, change the numbers to text. Example: 38 becomes thirty-eight

Example tone:
User: Cuaca hari ini gimana?
Assistant: Hari ini cuacanya cerah di sebagian besar wilayah, dengan suhu sekitar tigapuluh derajat.

User: Kamu tahu siapa presiden Indonesia?
Assistant: Presiden Indonesia saat ini adalah Joko Widodo.

User: ada berapa provinsi di Indonesia?
Assistant: Tigapuluh delapan.

If you're unsure about an answer, be honest and say that you don't know.
"""

# TODO: Inisialisasi klien Gemini dan konfigurasi prompt
# Gunakan genai.Client(api_key=...) untuk membuat klien.
# Gunakan types.GenerateContentConfig(system_instruction=...) untuk membuat konfigurasi awal.
# Jika ingin melihat contoh implementasi, baca dokumentasi resmi Gemini:
# https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started.ipynb
client = genai.Client(api_key=GOOGLE_API_KEY)
chat_config = types.GenerateContentConfig(system_instruction=system_instruction)
history_adapter = TypeAdapter(list[types.Content])

def angka_ke_teks(num):
    satuan = ['', 'satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan', 'sembilan']
    belasan = ['sepuluh', 'sebelas', 'dua belas', 'tiga belas', 'empat belas', 'lima belas', 
               'enam belas', 'tujuh belas', 'delapan belas', 'sembilan belas']
    puluhan = ['', 'sepuluh', 'dua puluh', 'tiga puluh', 'empat puluh', 'lima puluh', 
               'enam puluh', 'tujuh puluh', 'delapan puluh', 'sembilan puluh']
    
    if 0 <= num < 10:
        return satuan[num]
    elif 10 <= num < 20:
        return belasan[num - 10]
    elif 20 <= num < 100:
        return puluhan[num // 10] + (' ' + satuan[num % 10] if num % 10 != 0 else '')
    elif 100 <= num < 1000:
        if num == 100:
            return 'seratus'
        else:
            return ('seratus' if num // 100 == 1 else satuan[num // 100] + ' ratus') + \
                  ('' if num % 100 == 0 else ' ' + angka_ke_teks(num % 100))
    elif 1000 <= num < 1000000:
        if num == 1000:
            return 'seribu'
        else:
            return ('seribu' if num // 1000 == 1 else satuan[num // 1000] + ' ribu') + \
                  ('' if num % 1000 == 0 else ' ' + angka_ke_teks(num % 1000))
    elif 1000000 <= num < 1000000000:
        return satuan[num // 1000000] + ' juta' + \
              ('' if num % 1000000 == 0 else ' ' + angka_ke_teks(num % 1000000))
    elif 1000000000 <= num < 1000000000000:
        return satuan[num // 1000000000] + ' milyar' + \
              ('' if num % 1000000000 == 0 else ' ' + angka_ke_teks(num % 1000000000))
    else:
        return str(num)  

def ubah_angka_dalam_string(input_string):
    import re
    
    def ganti_angka(match):
        angka = int(match.group(0))
        return angka_ke_teks(angka)
    
    pattern = r'\b\d+\b'
    hasil = re.sub(pattern, ganti_angka, input_string)
    
    return hasil
# Fungsi untuk menyimpan/memuat riwayat chat
def export_chat_history(chat) -> str:
    return history_adapter.dump_json(chat.get_history()).decode("utf-8")

def save_chat_history(chat):
    json_history = export_chat_history(chat)
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write(json_history)

def load_chat_history():
    if not os.path.exists(CHAT_HISTORY_FILE):
        return client.chats.create(model=MODEL, config=chat_config)
    
    if os.path.getsize(CHAT_HISTORY_FILE) == 0:
        return client.chats.create(model=MODEL, config=chat_config)

    with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
        json_str = f.read().strip()

    if not json_str:
        return client.chats.create(model=MODEL, config=chat_config)

    try:
        history = history_adapter.validate_json(json_str)
        return client.chats.create(model=MODEL, config=chat_config, history=history)
    except Exception as e:
        print(f"[ERROR] Gagal load history chat: {e}")
        return client.chats.create(model=MODEL, config=chat_config)

# Inisialisasi sesi chat saat aplikasi dimulai
chat = load_chat_history()

# Kirim prompt ke LLM dan kembalikan respons teks
def generate_response(prompt: str) -> str:
    try:
        response = chat.send_message(prompt)
        save_chat_history(chat)
        result = ubah_angka_dalam_string(response.text.strip())
        return result
    except Exception as e:
        return f"[ERROR] {str(e)}"
