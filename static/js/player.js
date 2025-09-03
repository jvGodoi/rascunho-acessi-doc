import {
  elementoAudio, barra, tempoFinal, tempoInicial, botaoOuvir, botaoRepetir
} from './dom.js';
import { formatarTempo } from './util.js';

let repetirAtivado = false;

export function inicializarPlayer() {
  elementoAudio.addEventListener('loadedmetadata', () => {
    barra.max = elementoAudio.duration || 0;
    tempoFinal.textContent = formatarTempo(elementoAudio.duration);
    barra.style.background = `linear-gradient(to right, #3498db 0%, #ddd 0%)`;
  });

  elementoAudio.addEventListener('timeupdate', () => {
    barra.value = elementoAudio.currentTime || 0;
    tempoInicial.textContent = formatarTempo(elementoAudio.currentTime);
    const progresso = elementoAudio.duration ? (elementoAudio.currentTime / elementoAudio.duration) * 100 : 0;
    barra.style.background = `linear-gradient(to right, #3498db ${progresso}%, #ddd ${progresso}%)`;
  });

  elementoAudio.addEventListener('ended', () => {
    if (repetirAtivado) {
      elementoAudio.currentTime = 0;
      elementoAudio.play();
    } else {
      botaoOuvir.innerHTML = '<img src="/static/icones/fone.svg" alt="Ouvir"><span>Ouvir</span>';
    }
  });

  barra.addEventListener('input', () => {
    elementoAudio.currentTime = Number(barra.value || 0);
  });

  botaoOuvir.addEventListener('click', () => {
    if (elementoAudio.paused) {
      elementoAudio.play();
      botaoOuvir.innerHTML = '<img src="/static/icones/pause.svg" alt="Pausar"><span>Pausar</span>';
    } else {
      elementoAudio.pause();
      botaoOuvir.innerHTML = '<img src="/static/icones/fone.svg" alt="Ouvir"><span>Ouvir</span>';
    }
  });

  botaoRepetir.addEventListener('click', () => {
    repetirAtivado = !repetirAtivado;
    if (repetirAtivado) {
      botaoRepetir.classList.add('ativo');
      botaoRepetir.innerHTML = `<img src="/static/icones/repetir-ativo.svg" alt="Repetir Ativado"> <span>Repetir</span>`;
    } else {
      botaoRepetir.classList.remove('ativo');
      botaoRepetir.innerHTML = `<img src="/static/icones/repetir.svg" alt="Repetir"> <span>Repetir</span>`;
    }
  });
}
