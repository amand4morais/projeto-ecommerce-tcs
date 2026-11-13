const listaDetalhada = document.getElementById("lista-detalhada");
const painelResumo = document.getElementById("painel-resumo");
const linhasLog = document.getElementById("linhas-log");
const botaoDetalhado = document.getElementById("ver-detalhado");
const botaoResumo = document.getElementById("ver-resumo");
const TEXTO_VAZIO = "Nenhuma requisição ainda. Inicie a API e aguarde os clientes.";

let ultimoIdLog = 0;
let execucaoLog = null;

function limparTela() {
  listaDetalhada.replaceChildren(criarElemento("li", "vazio", TEXTO_VAZIO));
  const linha = criarElemento("tr", "vazio");
  const celula = criarElemento("td", null, TEXTO_VAZIO);
  celula.colSpan = 5;
  linha.append(celula);
  linhasLog.replaceChildren(linha);
}

function blocoCorpo(rotulo, conteudo) {
  const bloco = criarElemento("div", "bloco-corpo");
  bloco.append(criarElemento("p", "rotulo", rotulo), criarElemento("pre", "corpo", conteudo));
  return bloco;
}

function entradaDetalhada(r) {
  const entrada = criarElemento("li", "entrada");
  const titulo = criarElemento("div", "entrada-titulo");
  titulo.append(
    criarElemento("span", "hora", r.hora),
    criarElemento("span", "origem", r.ip),
    criarElemento("span", `metodo metodo-${r.metodo.toLowerCase()}`, r.metodo),
    criarElemento("span", "caminho", r.caminho),
    criarElemento("span", classeDoStatus(r.status), r.status),
  );
  entrada.append(titulo);

  const detalhes = criarElemento("div", "entrada-detalhes");
  const recebido = [r.autorizacao ? `Authorization: ${r.autorizacao}` : null, r.corpo_recebido].filter(Boolean).join("\n\n");
  detalhes.append(blocoCorpo("Recebido", recebido || "(sem corpo)"));
  detalhes.append(blocoCorpo(`Respondido · ${r.status}`, r.corpo_resposta || "(sem corpo)"));
  entrada.append(detalhes);
  return entrada;
}

function linhaResumo(r) {
  const linha = document.createElement("tr");
  const status = criarElemento("td");
  status.append(criarElemento("span", classeDoStatus(r.status), r.status));
  linha.append(
    criarElemento("td", "dados", r.hora),
    criarElemento("td", "dados", r.ip),
    criarElemento("td", "dados", r.metodo),
    criarElemento("td", "dados", r.caminho),
    status,
  );
  return linha;
}

function adicionarRegistros(registros) {
  if (registros.length === 0) return;
  listaDetalhada.querySelector(".vazio")?.remove();
  linhasLog.querySelector(".vazio")?.remove();
  for (const r of registros) {
    listaDetalhada.prepend(entradaDetalhada(r));
    linhasLog.prepend(linhaResumo(r));
    ultimoIdLog = r.id;
  }
}

async function buscarLog() {
  let log = await buscarJSON(`/log?desde=${ultimoIdLog}`);
  if (log.execucao !== execucaoLog) {
    // O servidor foi reiniciado: a numeração do log recomeçou.
    if (execucaoLog !== null) {
      limparTela();
      ultimoIdLog = 0;
      log = await buscarJSON("/log?desde=0");
    }
    execucaoLog = log.execucao;
  }
  adicionarRegistros(log.registros);
}

function alternarVisao(detalhado) {
  botaoDetalhado.setAttribute("aria-pressed", String(detalhado));
  botaoResumo.setAttribute("aria-pressed", String(!detalhado));
  listaDetalhada.hidden = !detalhado;
  painelResumo.hidden = detalhado;
}

async function atualizar() {
  try {
    await buscarLog();
  } catch {
    // Painel fora do ar: tenta de novo no próximo ciclo.
  }
}

botaoDetalhado.addEventListener("click", () => alternarVisao(true));
botaoResumo.addEventListener("click", () => alternarVisao(false));
document.getElementById("botao-limpar").addEventListener("click", limparTela);

atualizar();
setInterval(atualizar, 2000);
