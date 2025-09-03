import { zonaSoltar, entradaArquivo } from './dom.js';

export function inicializarDragDrop() {
  if (!zonaSoltar) return;

  zonaSoltar.addEventListener('dragover', (e) => {
    e.preventDefault();
    zonaSoltar.classList.add('arraste-sobre');
  });

  zonaSoltar.addEventListener('dragleave', () => {
    zonaSoltar.classList.remove('arraste-sobre');
  });

  zonaSoltar.addEventListener('drop', (e) => {
    e.preventDefault();
    zonaSoltar.classList.remove('arraste-sobre');
    const arquivos = e.dataTransfer.files;
    if (arquivos && arquivos.length > 0) {
      entradaArquivo.files = arquivos;
      entradaArquivo.dispatchEvent(new Event('change'));
    }
  });
}
