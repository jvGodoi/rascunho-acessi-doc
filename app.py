import os
import time
import asyncio
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from docx import Document
from langdetect import detect
import edge_tts
import re

# ===================== CONFIGURAÇÃO =====================
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = 'static/audio'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Mapeamento de vozes masculinas
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
        reader = PdfReader(filepath)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
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

    import time as t
    inicio = t.time()  # marca o início

    try:
        raw_text = extract_text(upload_path)
        text = clean_text(raw_text)
        lang = detect_lang(text)
        voice = pick_voice(lang)

        out_name = f"{os.path.splitext(filename)[0]}_{int(t.time())}.mp3"
        out_path = os.path.join(AUDIO_FOLDER, out_name)

        synthesize_to_mp3(text, voice, out_path)

        # calcula o tempo
        fim = t.time()
        duracao = fim - inicio
        if duracao < 60:
            print(f"[INFO] Conversão concluída em {duracao:.2f} segundos para '{filename}'")
        else:
            minutos = int(duracao // 60)
            segundos = int(duracao % 60)
            print(f"[INFO] Conversão concluída em {minutos} min {segundos} seg para '{filename}'")

        return jsonify(
            ok=True,
            filename=filename,
            detected_language=lang,
            voice=voice,
            audio_url=f"/audio/{out_name}"
        )
    except Exception as e:
        return jsonify(error=str(e)), 500
    finally:
        try:
            os.remove(upload_path)
        except Exception:
            pass

@app.route("/audio/<path:filename>")
def get_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename, as_attachment=False)

# ===================== MAIN =====================
if __name__ == "__main__":
    app.run(debug=True)
