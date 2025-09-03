import { entradaArquivo, infoAnexo } from './dom.js';
import { atualizarStatus, tamanhoHumano } from './util.js';

export function inicializarPreviewAnexo() {
  entradaArquivo.addEventListener('change', () => {
    const file = entradaArquivo.files[0];
    if (!file) {
      infoAnexo.innerHTML = `<h4>Nenhum Arquivo Selecionado</h4>`;
      atualizarStatus('', '');
      return;
    }

    const extensaoValida = ['pdf', 'docx', 'txt'];
    const nomeArquivo = file.name;
    const extensao = nomeArquivo.split('.').pop().toLowerCase();

    if (!extensaoValida.includes(extensao)) {
      alert('Formato não suportado. Selecione um arquivo .pdf, .docx ou .txt');
      entradaArquivo.value = '';
      infoAnexo.innerHTML = `<h4>Nenhum Arquivo Selecionado</h4>`;
      atualizarStatus('', '');
      return;
    }

    const tamanhoFormatado = tamanhoHumano(file.size);
    let icone = '/static/img/txt.png';
    if (extensao === 'pdf')  icone = '/static/icones/pdf.svg';
    if (extensao === 'docx') icone = '/static/icones/docx.svg';

    infoAnexo.innerHTML = `
      <div class="info-arquivo">
        <img src="${icone}" alt="Ícone do arquivo" class="icone-arquivo" />
        <div>
          <p class="nome-arquivo" title="${file.name}">${file.name}</p>
          <p class="tamanho-arquivo">${tamanhoFormatado}</p>
        </div>
      </div>
      <button class="botao-remover">✖ Remover Anexo</button>
    `;

    atualizarStatus('', '');
  });

  infoAnexo.addEventListener('click', (e) => {
    if (e.target.classList.contains('botao-remover')) {
      entradaArquivo.value = '';
      infoAnexo.innerHTML = `<h4>Nenhum Arquivo Selecionado</h4>`;
      atualizarStatus('', '');
    }
  });
}
