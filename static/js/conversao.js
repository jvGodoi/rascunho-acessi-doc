import {
  entradaArquivo, secaoPlayer, linkDownload, fonteAudio, elementoAudio,
  nomeAudioEl, metaAudioEl, sobreposicaoConversao, botaoConverter
} from './dom.js';
import { atualizarStatus, tamanhoHumano } from './util.js';
import { formatVoiceLabel, formatLanguageLabel } from './labels.js';

export function exibirPlayer(nomeArquivo, tamanho, caminhoAudio) {
  nomeAudioEl.textContent = nomeArquivo || 'Arquivo';
  metaAudioEl.textContent = `${tamanho} | mp3`;
  fonteAudio.src = caminhoAudio;
  elementoAudio.load();

  linkDownload.href = caminhoAudio;
  linkDownload.setAttribute('data-convertido', 'true');

  secaoPlayer.style.display = 'block';
}

export function inicializarConversao() {
  linkDownload.addEventListener('click', (e) => {
    const convertido = linkDownload.getAttribute('data-convertido');
    if (convertido !== 'true') {
      e.preventDefault();
      alert('Nenhum áudio disponível. Converta um arquivo primeiro.');
    }
  });

  botaoConverter.addEventListener('click', async () => {
    const file = entradaArquivo.files[0];
    if (!file) {
      alert('Por favor, selecione um arquivo para converter.');
      return;
    }

    sobreposicaoConversao.style.display = 'flex';

    const formData = new FormData();
    formData.append('file', file);

    const generoEscolhido = document.querySelector('input[name="preferred_gender"]:checked')?.value; // 'Female' | 'Male'
    if (generoEscolhido) formData.append('preferred_gender', generoEscolhido);

    try {
      const response = await fetch('/convert', { method: 'POST', body: formData });

      let dados;
      try {
        dados = await response.json();
      } catch {
        atualizarStatus('Erro inesperado na resposta do servidor.', 'erro');
        sobreposicaoConversao.style.display = 'none';
        return;
      }

      if (response.ok && dados.ok) {
        const tamanhoFormatado = tamanhoHumano(file.size);
        exibirPlayer(dados.filename || file.name, tamanhoFormatado, dados.audio_url);

        if (metaAudioEl) {
          const vozNome = formatVoiceLabel(dados.voice);
          const idiomaNome = formatLanguageLabel(dados.voice, dados.detected_language);
          metaAudioEl.innerHTML = `
            <span class="voz">Voz: ${vozNome}</span>
            <span class="idioma">Idioma: ${idiomaNome}</span>`;
        }

        atualizarStatus('Conversão concluída com sucesso!', 'sucesso');
      } else {
        atualizarStatus(dados.error || 'Erro ao converter o arquivo.', 'erro');
      }
    } catch (err) {
      console.error('Erro na requisição:', err);
      atualizarStatus('Erro ao enviar o arquivo para o servidor.', 'erro');
    } finally {
      sobreposicaoConversao.style.display = 'none';
    }
  });
}
