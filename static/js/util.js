import { statusDiv } from './dom.js';

export function atualizarStatus(texto, classe) {
  statusDiv.textContent = texto || '';
  statusDiv.className = 'mensagem-status ' + (classe || '');
}

export function formatarTempo(segundos) {
  const total = Math.floor(segundos || 0);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

export function tamanhoHumano(bytes) {
  if (!Number.isFinite(bytes)) return '--';
  return bytes >= 1024 * 1024
    ? (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    : (bytes / 1024).toFixed(1) + ' KB';
}
