import { elementoAudio, volumeRange, iconeVolume } from './dom.js';

export function inicializarVolume() {
  volumeRange.addEventListener('input', () => {
    elementoAudio.volume = Number(volumeRange.value);
    if (elementoAudio.volume === 0 || elementoAudio.muted) {
      iconeVolume.src = '/static/icones/som-mutado.svg';
    } else {
      iconeVolume.src = '/static/icones/volume.svg';
    }
  });

  iconeVolume.addEventListener('click', () => {
    elementoAudio.muted = !elementoAudio.muted;
    if (elementoAudio.muted) {
      iconeVolume.src = '/static/icones/som-mutado.svg';
    } else {
      iconeVolume.src = '/static/icones/volume.svg';
    }
  });
}
