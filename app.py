import os
import time
import asyncio
import re
import tempfile
import shutil
from typing import List
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from docx import Document
from langdetect import detect
from catalogo_vozes import vozes_por_idioma, voz_padrao_para_idioma, como_voz_publica
import edge_tts
from pydub import AudioSegment 

# ===================== CONFIGURAÇÃO =====================
app = Flask(__name__)
PASTA_UPLOADS = 'uploads'
PASTA_AUDIO = 'static/audio'
EXTENSOES_PERMITIDAS = {'pdf', 'docx', 'txt'}

os.makedirs(PASTA_UPLOADS, exist_ok=True)
os.makedirs(PASTA_AUDIO, exist_ok=True)

MAX_CHARS_TTS = 2800

VOZES_MASC = {
    "pt": "pt-BR-AntonioNeural",
    "en": "en-US-GuyNeural",
    "es": "es-ES-AlvaroNeural",
    "fr": "fr-FR-HenriNeural",
    "de": "de-DE-ConradNeural",
    "it": "it-IT-DiegoNeural",
    "ru": "ru-RU-DmitryNeural"
}
VOZES_FEM = {
    "pt": "pt-BR-FranciscaNeural",
    "en": "en-US-JennyNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "it": "it-IT-IsabellaNeural",
    "ru": "ru-RU-SvetlanaNeural",
}

# ===================== FUNÇÕES AUXILIARES =====================
def extensao_permitida(nome_arquivo: str) -> bool:
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS

def limpar_texto(texto: str) -> str:
    texto = re.sub(r'-\s*\n\s*', '', texto)   
    texto = re.sub(r'[ \t]+', ' ', texto)
    texto = re.sub(r'\s*\n\s*', '\n', texto)   
    texto = re.sub(r'\n{2,}', '\n', texto)
    return texto.strip()

def extrair_texto(caminho: str) -> str:
    ext = caminho.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        leitor = PdfReader(caminho)
        return "\n".join([pagina.extract_text() or "" for pagina in leitor.pages]).strip()
    elif ext == 'docx':
        doc = Document(caminho)
        return "\n".join([p.text for p in doc.paragraphs])
    elif ext == 'txt':
        with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    else:
        raise ValueError("Formato de arquivo não suportado.")

def detectar_idioma(texto: str) -> str:
    try:
        return detect(texto)
    except Exception:
        return "pt"

def escolher_voz_fallback(idioma: str, genero_preferido: str | None) -> str:
    lang = (idioma or "pt").split("-")[0].lower()
    if genero_preferido == "Female":
        return VOZES_FEM.get(lang, VOZES_FEM["pt"])
    if genero_preferido == "Male":
        return VOZES_MASC.get(lang, VOZES_MASC["pt"])
    return VOZES_MASC.get(lang, VOZES_MASC["pt"])

def _fatiar_por_limite(texto: str, max_chars: int) -> List[str]:

    partes = re.split(r'(?<=[\.\!\?])\s+|\n', texto)
    blocos = []
    atual = ""

    for p in partes:
        if not p:
            continue
        if len(atual) + len(p) + 1 <= max_chars:
            atual = (atual + " " + p).strip() if atual else p.strip()
        else:
            if atual:
                blocos.append(atual.strip())
            if len(p) > max_chars:
                inicio = 0
                while inicio < len(p):
                    blocos.append(p[inicio:inicio + max_chars].strip())
                    inicio += max_chars
                atual = ""
            else:
                atual = p.strip()

    if atual:
        blocos.append(atual.strip())

    return [b for b in blocos if b]

async def _sintetizar_bloco_async(texto_bloco: str, voz: str, caminho_mp3: str, tentativas: int = 3):

    ultimo_erro = None
    for _ in range(tentativas):
        try:
            comunicador = edge_tts.Communicate(texto_bloco, voice=voz)
            await comunicador.save(caminho_mp3)
            return
        except Exception as e:
            ultimo_erro = e
            await asyncio.sleep(0.8)
    raise RuntimeError(f"Falha ao sintetizar um bloco: {ultimo_erro}")

def _juntar_mp3(partes: List[str], destino: str):

    combinado = AudioSegment.silent(duration=0)
    for caminho in partes:
        segmento = AudioSegment.from_file(caminho, format="mp3")
        combinado += segmento
    combinado.export(destino, format="mp3", bitrate="192k")

def sintetizar_texto_grande_para_mp3(texto: str, voz: str, caminho_saida: str):

    blocos = _fatiar_por_limite(texto, MAX_CHARS_TTS)
    if not blocos:
        # nada para sintetizar -> gera 1s de silêncio p/ evitar erro de player
        AudioSegment.silent(duration=1000).export(caminho_saida, format="mp3")
        return

    tmp_dir = tempfile.mkdtemp(prefix="tts_parts_")
    arquivos_partes = []
    try:
        # sintetiza cada bloco sequencialmente
        for idx, bloco in enumerate(blocos, start=1):
            caminho_parte = os.path.join(tmp_dir, f"parte_{idx:04d}.mp3")
            asyncio.run(_sintetizar_bloco_async(bloco, voz, caminho_parte))
            arquivos_partes.append(caminho_parte)

        _juntar_mp3(arquivos_partes, caminho_saida)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

# ===================== ROTAS =====================
@app.route("/")
def pagina_inicial():
    return render_template("index.html")

@app.route("/convert", methods=["POST"])
def convert():
    if 'file' not in request.files:
        return jsonify(error="Nenhum arquivo enviado."), 400

    arquivo = request.files['file']
    if arquivo.filename == '':
        return jsonify(error="Nenhum arquivo selecionado."), 400

    if not extensao_permitida(arquivo.filename):
        return jsonify(error="Extensão não suportada."), 400

    nome_seguro = secure_filename(arquivo.filename)
    caminho_upload = os.path.join(PASTA_UPLOADS, nome_seguro)
    arquivo.save(caminho_upload)

    if os.path.getsize(caminho_upload) == 0:
        try:
            os.remove(caminho_upload)
        except Exception:
            pass
        return jsonify(error="O arquivo enviado está vazio (0 bytes)."), 400

    import time as t
    inicio = t.time()

    try:
        texto_bruto = extrair_texto(caminho_upload)
        texto = limpar_texto(texto_bruto)
        idioma = detectar_idioma(texto)  # ex.: 'pt'

        genero_preferido = request.form.get("preferred_gender")
        voz_usuario = request.form.get("voice")

        vozes_disponiveis = vozes_por_idioma(idioma)

        def voz_valida(vshort: str) -> bool:
            return any(vshort == v["shortName"] for v in vozes_disponiveis)

        if voz_usuario and voz_valida(voz_usuario):
            voz_escolhida = voz_usuario
        else:
            voz_escolhida = voz_padrao_para_idioma(idioma, genero_preferido)
            if not voz_escolhida:
                voz_escolhida = escolher_voz_fallback(idioma, genero_preferido)

        nome_saida = f"{os.path.splitext(nome_seguro)[0]}_{int(t.time())}.mp3"
        caminho_saida = os.path.join(PASTA_AUDIO, nome_saida)

        sintetizar_texto_grande_para_mp3(texto, voz_escolhida, caminho_saida)

        duracao = t.time() - inicio
        if duracao < 60:
            print(f"[INFO] Conversão concluída em {duracao:.2f} segundos para '{nome_seguro}'")
        else:
            m, s = divmod(int(duracao), 60)
            print(f"[INFO] Conversão concluída em {m} min {s} seg para '{nome_seguro}'")

        return jsonify(
            ok=True,
            filename=nome_seguro,
            detected_language=idioma,
            voice=voz_escolhida,
            available_voices=[como_voz_publica(v) for v in vozes_disponiveis],
            audio_url=f"/audio/{nome_saida}"
        )
    except Exception as e:
        return jsonify(error=str(e)), 500
    finally:
        try:
            os.remove(caminho_upload)
        except Exception:
            pass

@app.route("/audio/<path:filename>")
def obter_audio(filename):
    return send_from_directory(PASTA_AUDIO, filename, as_attachment=False)

if __name__ == "__main__":
    app.run(debug=True)
