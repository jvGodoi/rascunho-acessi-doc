const arquivoInput = document.getElementById('arquivoInput');
const anexoInfo = document.getElementById('anexoInfo');
const converterBtn = document.querySelector('.btn');
const statusDiv = document.getElementById('status-conversao');
const playerSection = document.getElementById('player-section');

const audio = document.getElementById('audio');
const barra = document.getElementById('barra-progresso');
const tempoInicial = document.getElementById('tempo-inicial');
const tempoFinal = document.getElementById('tempo-final');
const playBtn = document.getElementById('play-btn');
const repetirBtn = document.getElementById('repetir-btn');
const volume = document.getElementById('volume');
const volumeIcon = document.getElementById('volume-icon');


let repetirAtivado = false;


function atualizarStatus(texto, classe) {
  statusDiv.textContent = texto;
  statusDiv.className = 'status-mensagem ' + classe;
}

arquivoInput.addEventListener('change', () => {
  const file = arquivoInput.files[0];
  if (file) {
    const extensaoValida = ['pdf', 'docx', 'txt'];
    const nomeArquivo = file.name;
    const extensao = nomeArquivo.split('.').pop().toLowerCase();

    if (!extensaoValida.includes(extensao)) {
      alert("Formato não suportado. Selecione um arquivo .pdf, .docx ou .txt");
      arquivoInput.value = '';
      anexoInfo.innerHTML = `<h4>Nenhum Arquivo Selecionado</h4>`;
      atualizarStatus('', '');
      return;
    }

    let tamanhoFormatado = (file.size >= 1024 * 1024) ?
      (file.size / (1024 * 1024)).toFixed(1) + " MB" :
      (file.size / 1024).toFixed(1) + " KB";

    let icone = "/static/icones/arquivo-anexado.svg";
    if (extensao === "pdf") icone = "/static/icones/pdf.svg";
    if (extensao === "docx") icone = "/static/icones/docx.svg";

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
  }
});

anexoInfo.addEventListener('click', (e) => {
  if (e.target.classList.contains('remove-btn')) {
    arquivoInput.value = '';
    anexoInfo.innerHTML = `<h4>Nenhum Arquivo Selecionado</h4>`;
    atualizarStatus('', '');
  }
});

function exibirPlayer(nomeArquivo, tamanho, caminhoAudio) {
  document.getElementById('audio-nome').textContent = nomeArquivo;
  document.getElementById('audio-meta').textContent = `${tamanho} | mp3`;
  document.getElementById('audio-src').src = caminhoAudio;
setTimeout(() => {
  document.getElementById('audio').load();
}, 100);
  document.getElementById('audio').load();
  document.getElementById('link-download').href = caminhoAudio;
  document.getElementById('link-download').setAttribute('data-convertido', 'true');
  playerSection.style.display = 'block';
}
const linkDownload = document.getElementById('link-download');

linkDownload.addEventListener('click', function(e) {
  const convertido = linkDownload.getAttribute('data-convertido');

  if (convertido !== 'true') {
    e.preventDefault(); // Impede o download
    alert("Nenhum áudio disponível. Converta um arquivo primeiro.");
  }
});

const overlayConversao = document.getElementById('overlay-conversao');

converterBtn.addEventListener('click', async () => {
  const file = arquivoInput.files[0];
  if (!file) {
    alert("Por favor, selecione um arquivo para converter.");
    return;
  }

  overlayConversao.style.display = 'flex'; // Mostra o modal
  /* atualizarStatus("Convertendo, por favor aguarde...", "aguarde"); */

  const formData = new FormData();
  formData.append("arquivo", file);

  try {
    const response = await fetch("/converter", {
      method: "POST",
      body: formData
    });

    let dados;
    try {
      dados = await response.json();
    } catch {
      atualizarStatus("Erro inesperado na resposta do servidor.", "erro");
      overlayConversao.style.display = 'none';
      return;
    }

    if (response.ok) {
      const tamanhoFormatado = (dados.tamanho >= 1024 * 1024)
        ? (dados.tamanho / (1024 * 1024)).toFixed(1) + " MB"
        : (dados.tamanho / 1024).toFixed(1) + " KB";

      exibirPlayer(dados.nome, tamanhoFormatado, dados.audio_url);
      /* atualizarStatus("Conversão concluída com sucesso!", "sucesso"); */
    } else {
      atualizarStatus(dados.erro || "Erro ao converter o arquivo.", "erro");
    }
  } catch (err) {
    console.error("Erro na requisição:", err);
    atualizarStatus("Erro ao enviar o arquivo para o servidor.", "erro");
  } finally {
    overlayConversao.style.display = 'none'; // Oculta após terminar
  }
});

// Player personalizado
function formatarTempo(segundos) {
  const totalSegundos = Math.floor(segundos);

  const horas = Math.floor(totalSegundos / 3600);
  const minutos = Math.floor((totalSegundos % 3600) / 60);
  const seg = totalSegundos % 60;

  const strMin = String(minutos).padStart(2, '0');
  const strSeg = String(seg).padStart(2, '0');

  if (horas > 0) {
    return `${horas}:${strMin}:${strSeg}`; // formato HH:MM:SS
  } else {
    return `${strMin}:${strSeg}`;          // formato MM:SS
  }
}

audio.addEventListener('loadedmetadata', () => {
  barra.max = audio.duration;
  tempoFinal.textContent = formatarTempo(audio.duration);
  barra.style.background = `linear-gradient(to right, #3498db 0%, #ddd 0%)`;
});

audio.addEventListener('timeupdate', () => {
  barra.value = audio.currentTime;
  tempoInicial.textContent = formatarTempo(audio.currentTime);
  const progresso = (audio.currentTime / audio.duration) * 100;
  barra.style.background = `linear-gradient(to right, #3498db ${progresso}%, #ddd ${progresso}%)`;

  tempoInicial.textContent = formatarTempo(audio.currentTime);
});

audio.addEventListener('ended', () => {
  if (repetirAtivado) {
    audio.currentTime = 0;
    audio.play();
  }
});

barra.addEventListener('input', () => {
  audio.currentTime = barra.value;
});

playBtn.addEventListener('click', () => {
  if (audio.paused) {
    audio.play();
    playBtn.innerHTML = '<img src="static/icones/pause.svg" <span>Pausar</span>';
  } else {
    audio.pause();
    playBtn.innerHTML = '<img src="static/icones/fone.svg" <span>Ouvir</span>';
  }
});

repetirBtn.addEventListener('click', () => {
  repetirAtivado = !repetirAtivado; // alterna entre true e false

  if (repetirAtivado) {
    repetirBtn.classList.add('ativo');
    repetirBtn.innerHTML = `<img src="/static/icones/repetir-ativo.svg" alt="Repetir Ativado"> Repetir`;
  } else {
    repetirBtn.classList.remove('ativo');
    repetirBtn.innerHTML = `<img src="/static/icones/repetir.svg" alt="Repetir"> Repetir`;
  }
});

function repetirAudio() {
  audio.currentTime = 0;
  audio.play();
}

volume.addEventListener('input', () => {
  audio.volume = volume.value;
});

volumeIcon.addEventListener('click', () => {
  audio.muted = !audio.muted;

  if (audio.muted) {
    volumeIcon.src = "/static/icones/som-mutado.svg";  // ícone de som desligado
  } else {
    volumeIcon.src = "/static/icones/volume.svg"; // ícone de som normal
  }
});

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
  if (arquivos.length > 0) {
    arquivoInput.files = arquivos;
    // Dispara evento de "change" para exibir preview
    arquivoInput.dispatchEvent(new Event('change'));
  }
});