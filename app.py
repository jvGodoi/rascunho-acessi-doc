import os
import re
import time
import asyncio
import tempfile
import subprocess
from typing import List

from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from docx import Document
from langdetect import detect
from catalogo_vozes import vozes_por_idioma, voz_padrao_para_idioma, como_voz_publica
import edge_tts

# ===================== CONFIGURAÇÃO =====================
app = Flask(__name__)
PASTA_UPLOADS = 'uploads'
PASTA_AUDIO = 'static/audio'
EXTENSOES_PERMITIDAS = {'pdf', 'docx', 'txt'}

os.makedirs(PASTA_UPLOADS, exist_ok=True)
os.makedirs(PASTA_AUDIO, exist_ok=True)

# Fallbacks locais caso o catálogo não retorne nada
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
    # Normaliza quebras e espaços; remove hífen de quebra de linha
    texto = re.sub(r'-\s*\n\s*', '', texto)            # junta palavras hifenizadas no fim de linha
    texto = re.sub(r'[ \t]+', ' ', texto)              # colapsa múltiplos espaços/tabs
    texto = re.sub(r'\s*\n\s*', '\n', texto)           # normaliza quebras de linha
    texto = re.sub(r'\n{2,}', '\n\n', texto)           # mantém parágrafos
    return texto.strip()

def extrair_texto(caminho: str) -> str:
    ext = caminho.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        leitor = PdfReader(caminho)
        # alguns PDFs retornam None em páginas sem texto extraível
        return "\n".join(filter(None, [(p.extract_text() or "") for p in leitor.pages])).strip()
    elif ext == 'docx':
        doc = Document(caminho)
        return "\n".join(p.text for p in doc.paragraphs).strip()
    elif ext == 'txt':
        with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
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

def dividir_em_blocos(texto: str, max_chars: int = 2800) -> List[str]:
    """
    Divide o texto grande em blocos menores respeitando pontos finais sempre que possível.
    'max_chars' pode ser ajustado entre ~2200 e 3000.
    """
    texto = texto.strip()
    if not texto:
        return []
    if len(texto) <= max_chars:
        return [texto]

    blocos = []
    inicio = 0
    n = len(texto)

    while inicio < n:
        fim = min(inicio + max_chars, n)
        # tenta cortar no último ponto próximo ao fim do bloco
        corte = texto.rfind('.', inicio, fim)
        # se não achar ponto razoável, corta bruto
        if corte == -1 or corte <= inicio + int(max_chars * 0.6):
            corte = fim
        else:
            corte += 1  # inclui o ponto

        bloco = texto[inicio:corte].strip()
        if bloco:
            blocos.append(bloco)
        inicio = corte

    return blocos

async def sintetizar_bloco_async(texto: str, voz: str, caminho_saida: str):
    comunicador = edge_tts.Communicate(texto, voice=voz)
    await comunicador.save(caminho_saida)

def sintetizar_varios_blocos_para_mp3(blocos: List[str], voz: str, caminho_final: str):
    """
    Gera um MP3 para cada bloco (arquivos temporários) e concatena tudo com ffmpeg (sem re-encode).
    Requer ffmpeg instalado (no Render, adicione 'ffmpeg' no apt.txt).
    """
    if not blocos:
        raise ValueError("Sem conteúdo para sintetizar.")

    tmpfiles = []
    list_path = None
    try:
        # 1) sintetiza cada bloco
        for i, bloco in enumerate(blocos, start=1):
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3", prefix=f"chunk_{i:03d}_")
            os.close(fd)
            asyncio.run(sintetizar_bloco_async(bloco, voz, tmp_path))
            tmpfiles.append(tmp_path)

        # 2) cria lista para concat demuxer
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f_list:
            list_path = f_list.name
            for p in tmpfiles:
                f_list.write(f"file '{os.path.abspath(p)}'\n")

        # 3) concatena sem re-encode
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            caminho_final
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Falha no ffmpeg concat: {proc.stderr[:500]}")

    finally:
        for p in tmpfiles:
            try:
                os.remove(p)
            except:
                pass
        if list_path:
            try:
                os.remove(list_path)
            except:
                pass

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
        if not texto:
            return jsonify(error="Não foi possível extrair texto do arquivo."), 400

        idioma = detectar_idioma(texto)  # ex.: 'pt'
        genero_preferido = request.form.get("preferred_gender")  # 'Male' | 'Female' | None
        voz_usuario = request.form.get("voice")                  # ex.: 'pt-BR-FranciscaNeural'

        # Lista de vozes possíveis para o idioma detectado
        vozes_disponiveis = vozes_por_idioma(idioma)

        def voz_valida(vshort: str) -> bool:
            return any(vshort == v.get("shortName") for v in vozes_disponiveis)

        if voz_usuario and voz_valida(voz_usuario):
            voz_escolhida = voz_usuario
        else:
            voz_escolhida = voz_padrao_para_idioma(idioma, genero_preferido)
            if not voz_escolhida:
                voz_escolhida = escolher_voz_fallback(idioma, genero_preferido)

        # Saída final
        nome_saida = f"{os.path.splitext(nome_seguro)[0]}_{int(t.time())}.mp3"
        caminho_saida = os.path.join(PASTA_AUDIO, nome_saida)

        # Divide e sintetiza em blocos para garantir áudio completo
        blocos = dividir_em_blocos(texto, max_chars=2800)
        sintetizar_varios_blocos_para_mp3(blocos, voz_escolhida, caminho_saida)

        # Log de tempo
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

# ===================== MAIN =====================
if __name__ == "__main__":
    # Em produção (Render), use gunicorn: web: gunicorn app:app
    app.run(debug=True)
