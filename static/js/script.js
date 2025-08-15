// ===== Seletores principais =====
const arquivoInput   = document.getElementById('arquivoInput');
const anexoInfo      = document.getElementById('anexoInfo');
const converterBtn   = document.querySelector('.btn');
const statusDiv      = document.getElementById('status-conversao');
const playerSection  = document.getElementById('player-section');

const audio          = document.getElementById('audio');
const source         = document.getElementById('audio-src');
const barra          = document.getElementById('barra-progresso');
const tempoInicial   = document.getElementById('tempo-inicial');
const tempoFinal     = document.getElementById('tempo-final');
const playBtn        = document.getElementById('play-btn');
const repetirBtn     = document.getElementById('repetir-btn');
const volumeRange    = document.getElementById('volume');
const volumeIcon     = document.getElementById('volume-icon');
const linkDownload   = document.getElementById('link-download');
const overlayConversao = document.getElementById('overlay-conversao');

let repetirAtivado = false;

// ===== Utilitários =====
function atualizarStatus(texto, classe) {
  statusDiv.textContent = texto || '';
  statusDiv.className = 'status-mensagem ' + (classe || '');
}

function formatarTempo(segundos) {
  const total = Math.floor(segundos || 0);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;

  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

function tamanhoHumano(bytes) {
  if (!Number.isFinite(bytes)) return '--';
  return bytes >= 1024 * 1024
    ? (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    : (bytes / 1024).toFixed(1) + ' KB';
}

// ===== Preview e remoção do anexo =====
arquivoInput.addEventListener('change', () => {
  const file = arquivoInput.files[0];
  if (!file) {
    anexoInfo.innerHTML = `<h4>Nenhum Arquivo Selecionado</h4>`;
    atualizarStatus('', '');
    return;
  }

  const extensaoValida = ['pdf', 'docx', 'txt'];
  const nomeArquivo = file.name;
  const extensao = nomeArquivo.split('.').pop().toLowerCase();

  if (!extensaoValida.includes(extensao)) {
    alert('Formato não suportado. Selecione um arquivo .pdf, .docx ou .txt');
    arquivoInput.value = '';
    anexoInfo.innerHTML = `<h4>Nenhum Arquivo Selecionado</h4>`;
    atualizarStatus('', '');
    return;
  }

  const tamanhoFormatado = tamanhoHumano(file.size);

  let icone = '/static/icones/arquivo-anexado.svg';
  if (extensao === 'pdf')  icone = '/static/icones/pdf.svg';
  if (extensao === 'docx') icone = '/static/icones/docx.svg';

  anexoInfo.innerHTML = `
    <div class="info">
      <img src="${icone}" alt="Ícone Arquivo" class="file-icon" />
      <div>
        <p class="file-name" title="${file.name}">${file.name}</p>
        <p class="file-size">${tamanhoFormatado}</p>
      </div>
    </div>
    <button class="remove-btn">✖ Remover Anexo</button>
  `;

  atualizarStatus('', '');
});

anexoInfo.addEventListener('click', (e) => {
  if (e.target.classList.contains('remove-btn')) {
    arquivoInput.value = '';
    anexoInfo.innerHTML = `<h4>Nenhum Arquivo Selecionado</h4>`;
    atualizarStatus('', '');
  }
});

// ===== Exibir player =====
function exibirPlayer(nomeArquivo, tamanho, caminhoAudio) {
  document.getElementById('audio-nome').textContent = nomeArquivo || 'Arquivo';
  document.getElementById('audio-meta').textContent = `${tamanho} | mp3`;
  source.src = caminhoAudio;
  audio.load();

  linkDownload.href = caminhoAudio;
  linkDownload.setAttribute('data-convertido', 'true');

  playerSection.style.display = 'block';
}

// Bloqueia download sem áudio
linkDownload.addEventListener('click', function (e) {
  const convertido = linkDownload.getAttribute('data-convertido');
  if (convertido !== 'true') {
    e.preventDefault();
    alert('Nenhum áudio disponível. Converta um arquivo primeiro.');
  }
});

// ===== Envio para conversão =====
converterBtn.addEventListener('click', async () => {
  const file = arquivoInput.files[0];
  if (!file) {
    alert('Por favor, selecione um arquivo para converter.');
    return;
  }

  overlayConversao.style.display = 'flex';

  const formData = new FormData();
  formData.append('file', file); // campo esperado pelo back-end

  try {
    const response = await fetch('/convert', {
      method: 'POST',
      body: formData
    });

    let dados;
    try {
      dados = await response.json();
    } catch {
      atualizarStatus('Erro inesperado na resposta do servidor.', 'erro');
      overlayConversao.style.display = 'none';
      return;
    }

    if (response.ok && dados.ok) {
      const tamanhoFormatado = tamanhoHumano(file.size);
      exibirPlayer(dados.filename || file.name, tamanhoFormatado, dados.audio_url);

      // Mostra voz/idioma
      const meta = document.getElementById('audio-meta');
      if (meta) {
        meta.textContent = `Voz: ${dados.voice} | Idioma: ${dados.detected_language}`;
      }

      atualizarStatus('Conversão concluída com sucesso!', 'sucesso');
    } else {
      atualizarStatus(dados.error || 'Erro ao converter o arquivo.', 'erro');
    }
  } catch (err) {
    console.error('Erro na requisição:', err);
    atualizarStatus('Erro ao enviar o arquivo para o servidor.', 'erro');
  } finally {
    overlayConversao.style.display = 'none';
  }
});

// ===== Player personalizado =====
audio.addEventListener('loadedmetadata', () => {
  barra.max = audio.duration || 0;
  tempoFinal.textContent = formatarTempo(audio.duration);
  // estado inicial da barra
  barra.style.background = `linear-gradient(to right, #3498db 0%, #ddd 0%)`;
});

audio.addEventListener('timeupdate', () => {
  barra.value = audio.currentTime || 0;
  tempoInicial.textContent = formatarTempo(audio.currentTime);
  const progresso = audio.duration ? (audio.currentTime / audio.duration) * 100 : 0;
  barra.style.background = `linear-gradient(to right, #3498db ${progresso}%, #ddd ${progresso}%)`;
});

audio.addEventListener('ended', () => {
  if (repetirAtivado) {
    audio.currentTime = 0;
    audio.play();
  } else {
    // volta o botão para "Ouvir"
    playBtn.innerHTML = '<img src="/static/icones/fone.svg" alt="Ouvir"><span>Ouvir</span>';
  }
});

barra.addEventListener('input', () => {
  audio.currentTime = Number(barra.value || 0);
});

playBtn.addEventListener('click', () => {
  if (audio.paused) {
    audio.play();
    playBtn.innerHTML = '<img src="/static/icones/pause.svg" alt="Pausar"><span>Pausar</span>';
  } else {
    audio.pause();
    playBtn.innerHTML = '<img src="/static/icones/fone.svg" alt="Ouvir"><span>Ouvir</span>';
  }
});

repetirBtn.addEventListener('click', () => {
  repetirAtivado = !repetirAtivado;
  if (repetirAtivado) {
    repetirBtn.classList.add('ativo');
    repetirBtn.innerHTML = `<img src="/static/icones/repetir-ativo.svg" alt="Repetir Ativado"> <span>Repetir</span>`;
  } else {
    repetirBtn.classList.remove('ativo');
    repetirBtn.innerHTML = `<img src="/static/icones/repetir.svg" alt="Repetir"> <span>Repetir</span>`;
  }
});

// Volume
volumeRange.addEventListener('input', () => {
  audio.volume = Number(volumeRange.value);
  if (audio.volume === 0 || audio.muted) {
    volumeIcon.src = '/static/icones/som-mutado.svg';
  } else {
    volumeIcon.src = '/static/icones/volume.svg';
  }
});

volumeIcon.addEventListener('click', () => {
  audio.muted = !audio.muted;
  if (audio.muted) {
    volumeIcon.src = '/static/icones/som-mutado.svg';
  } else {
    volumeIcon.src = '/static/icones/volume.svg';
  }
});

// ===== Drag & Drop =====
const dropZone = document.getElementById('drop-zone');

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const arquivos = e.dataTransfer.files;
  if (arquivos && arquivos.length > 0) {
    arquivoInput.files = arquivos;
    arquivoInput.dispatchEvent(new Event('change'));
  }
});
