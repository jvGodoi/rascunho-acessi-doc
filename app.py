import os
import time
import asyncio
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from docx import Document
from langdetect import detect
from voices_catalog import voices_for_lang, default_voice_for_lang, as_public_voice
import edge_tts
import re
import io
from PIL import Image
import fitz  # PyMuPDF
import pytesseract

# ===================== CONFIGURAÇÃO =====================
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'static/audio'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# Mapeamento de vozes masculinas

# Mapeia o lang detectado (ex.: 'pt', 'en', 'es-ES') para códigos do Tesseract
TESSERACT_LANG_MAP = {
    "pt": "por",
    "pt-BR": "por",
    "pt-PT": "por",
    "en": "eng",
    "en-US": "eng",
    "en-GB": "eng",
    "es": "spa",
    "es-ES": "spa",
    "fr": "fra",
    "de": "deu",
    "it": "ita",
    "ru": "rus",
}

def pick_tesseract_lang(lang_detected: str, fallback: str = "por+eng") -> str:
    """
    Converte o idioma detectado (langdetect) para o código Tesseract.
    Se não souber, retorna 'por+eng' como default razoável para BR.
    """
    if not lang_detected:
        return fallback
    # tenta match exato, senão tenta prefixo (ex.: 'es-ES' -> 'es')
    if lang_detected in TESSERACT_LANG_MAP:
        return TESSERACT_LANG_MAP[lang_detected]
    prefix = lang_detected.split("-")[0]
    return TESSERACT_LANG_MAP.get(prefix, fallback)

def extract_text_with_ocr(pdf_path: str, tess_lang: str = "por+eng", dpi: int = 200) -> str:
    """
    Faz OCR de cada página do PDF usando PyMuPDF (render) + Tesseract.
    - dpi 200~300 costuma dar bom equilíbrio entre velocidade/qualidade.
    """
    text_parts = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            # Renderiza a página em imagem (PNG em memória)
            pix = page.get_pixmap(dpi=dpi)  # maior DPI = melhor OCR, mais lento
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            # OCR
            page_text = pytesseract.image_to_string(img, lang=tess_lang)
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()

def looks_like_scanned_or_empty(extracted_text: str, min_len: int = 50) -> bool:
    """
    Heurística simples: se texto é muito curto ou vazio, provavelmente é escaneado.
    """
    if not extracted_text:
        return True
    # remove espaços/quebras para medir conteúdo real
    compact = "".join(extracted_text.split())
    return len(compact) < min_len

VOICES_MASC = {
    "pt": "pt-BR-AntonioNeural",
    "en": "en-US-GuyNeural",
    "es": "es-ES-AlvaroNeural",
    "fr": "fr-FR-HenriNeural",
    "de": "de-DE-ConradNeural",
    "it": "it-IT-DiegoNeural",
    "ru": "ru-RU-DmitryNeural"
}

# ===================== FUNÇÕES AUXILIARES =====================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_text(text):
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\s*\n\s*', ' ', text)
    text = re.sub(r'-\s+', '', text)
    return text.strip()

def extract_text(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()

    if ext == 'pdf':
        # 1) tenta extrair com PyPDF2 (texto “verdadeiro” embutido)
        reader = PdfReader(filepath)
        pdf_text = "\n".join([page.extract_text() or "" for page in reader.pages]).strip()

        # 2) se não veio texto útil, tenta OCR (escaneado)
        if looks_like_scanned_or_empty(pdf_text):
            # você pode escolher o idioma de OCR de duas formas:
            #   a) usar a detecção posterior (detect_lang) — precisa ler o arquivo inteiro (já fazemos depois)
            #   b) assumir um default "por+eng" para BR
            tess_lang = "por+eng"  # default razoável
            try:
                # se quiser “adivinhar” melhor, dá pra tentar detectar um idioma
                # rapidamente com pytesseract em uma página, mas manteremos simples.
                pdf_text = extract_text_with_ocr(filepath, tess_lang=tess_lang, dpi=220)
            except Exception as ocr_err:
                # Opcional: log para diagnóstico
                print(f"[WARN] OCR falhou: {ocr_err}")
                # Se OCR falhar, devolve o que tiver (mesmo que vazio)
                return pdf_text

        return pdf_text

    elif ext == 'docx':
        doc = Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs])

    elif ext == 'txt':
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    else:
        raise ValueError("Formato não suportado.")

def detect_lang(text):
    try:
        return detect(text)
    except:
        return "pt"

def pick_voice(lang):
    return VOICES_MASC.get(lang, VOICES_MASC["pt"])

async def synthesize_async(text, voice, out_path):
    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(out_path)

def synthesize_to_mp3(text, voice, out_path):
    asyncio.run(synthesize_async(text, voice, out_path))

# ===================== ROTAS =====================
@app.route("/")
def index():
    return render_template("index.html")
# app.py


@app.route("/convert", methods=["POST"])
def convert():
    if 'file' not in request.files:
        return jsonify(error="Nenhum arquivo enviado."), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(error="Nenhum arquivo selecionado."), 400

    if not allowed_file(file.filename):
        return jsonify(error="Extensão não suportada."), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(upload_path)
    if os.path.getsize(upload_path) == 0:
        try:
            os.remove(upload_path)
        except Exception:
            pass
        return jsonify(error="O arquivo enviado está vazio (0 bytes)."), 400
    
    
    import time as t
    inicio = t.time()

    try:
        raw_text = extract_text(upload_path)
        text = clean_text(raw_text)
        lang = detect_lang(text)  # ex.: 'pt'

        # 👇 lê a preferência do usuário
        preferred_gender = request.form.get("preferred_gender")  # 'Male' | 'Female' | None

        # Se o usuário especificar uma voz exata (opcional):
        user_voice = request.form.get("voice")  # ex.: 'pt-BR-FranciscaNeural'

        # Lista de vozes possíveis para o idioma detectado
        available = voices_for_lang(lang)

        # Valida a voz exata, se enviada
        def is_valid_voice(vshort):
            return any(vshort == v["shortName"] for v in available)

        if user_voice and is_valid_voice(user_voice):
            voice = user_voice
        else:
            # Escolhe padrão respeitando o gênero quando possível
            voice = default_voice_for_lang(lang, prefer_gender=preferred_gender)
            # Fallback absoluto, caso não haja catálogo:
            if not voice:
                voice = pick_voice(lang)  # sua função antiga

        out_name = f"{os.path.splitext(filename)[0]}_{int(t.time())}.mp3"
        out_path = os.path.join(AUDIO_FOLDER, out_name)

        synthesize_to_mp3(text, voice, out_path)

        # Log de tempo (em seg ou min+seg)
        duracao = t.time() - inicio
        if duracao < 60:
            print(f"[INFO] Conversão concluída em {duracao:.2f} segundos para '{filename}'")
        else:
            m, s = divmod(int(duracao), 60)
            print(f"[INFO] Conversão concluída em {m} min {s} seg para '{filename}'")

        return jsonify(
            ok=True,
            filename=filename,
            detected_language=lang,
            voice=voice,
            available_voices=[as_public_voice(v) for v in available],  # opcional: lista pro front
            audio_url=f"/audio/{out_name}"
        )
    except Exception as e:
        return jsonify(error=str(e)), 500
    finally:
        try: os.remove(upload_path)
        except Exception: pass
        
@app.route("/audio/<path:filename>")
def get_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename, as_attachment=False)

# ===================== MAIN =====================
if __name__ == "__main__":
    app.run(debug=True)
