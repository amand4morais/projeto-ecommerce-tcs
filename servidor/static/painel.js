const campoPorta = document.getElementById("porta");
const botaoIniciar = document.getElementById("botao-iniciar");
const botaoParar = document.getElementById("botao-parar");
const caixaEstado = document.getElementById("estado");
const textoEstado = document.getElementById("texto-estado");
const mensagem = document.getElementById("mensagem");
const linhasLog = document.getElementById("linhas-log");

let ultimoIdLog = 0;
let execucaoLog = null;

function mostrarMensagem(texto, ehErro) {
  mensagem.textContent = texto;
  mensagem.classList.toggle("erro", Boolean(ehErro));
}

function aplicarEstado(estado) {
  caixaEstado.dataset.rodando = String(estado.rodando);
  textoEstado.textContent = estado.rodando ? `API rodando na porta ${estado.porta}` : "API parada";
  campoPorta.disabled = estado.rodando;
  botaoIniciar.disabled = estado.rodando;
  botaoParar.disabled = !estado.rodando;
  if (estado.rodando) campoPorta.value = estado.porta;
}

async function enviar(caminho, corpo) {
  try {
    const resposta = await fetch(caminho, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo || {}),
    });
    const dados = await resposta.json();
    mostrarMensagem(dados.mensagem, !resposta.ok);
    if (resposta.ok) aplicarEstado(dados);
  } catch (erro) {
    mostrarMensagem("Não foi possível falar com o painel. Ele ainda está rodando no terminal?", true);
  }
}

function adicionarLinhas(registros) {
  if (registros.length === 0) return;
  const vazio = linhasLog.querySelector("tr.vazio");
  if (vazio) vazio.remove();
  for (const r of registros) {
    const linha = document.createElement("tr");
    const classeStatus = r.status < 400 ? "status-ok" : "status-erro";
    for (const valor of [r.hora, r.ip, r.metodo, r.caminho]) {
      const celula = document.createElement("td");
      celula.textContent = valor;
      linha.appendChild(celula);
    }
    const celulaStatus = document.createElement("td");
    celulaStatus.textContent = r.status;
    celulaStatus.className = classeStatus;
    linha.appendChild(celulaStatus);
    linhasLog.prepend(linha);
    ultimoIdLog = r.id;
  }
}

function reiniciarTabela() {
  linhasLog.replaceChildren();
  const linha = document.createElement("tr");
  linha.className = "vazio";
  const celula = document.createElement("td");
  celula.colSpan = 5;
  celula.textContent = "Nenhuma requisição ainda. Inicie a API e aguarde os clientes.";
  linha.appendChild(celula);
  linhasLog.appendChild(linha);
  ultimoIdLog = 0;
}

async function buscarLog() {
  let log = await fetch(`/log?desde=${ultimoIdLog}`).then((r) => r.json());
  if (log.execucao !== execucaoLog) {
    // O servidor foi reiniciado: a numeração do log recomeçou.
    if (execucaoLog !== null) {
      reiniciarTabela();
      log = await fetch("/log?desde=0").then((r) => r.json());
    }
    execucaoLog = log.execucao;
  }
  adicionarLinhas(log.registros);
}

async function atualizar() {
  try {
    aplicarEstado(await fetch("/estado").then((r) => r.json()));
    await buscarLog();
  } catch (erro) {
    // Painel fora do ar: tenta de novo no próximo ciclo.
  }
}

botaoIniciar.addEventListener("click", () => enviar("/iniciar", { porta: campoPorta.value }));
botaoParar.addEventListener("click", () => enviar("/parar"));
campoPorta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !botaoIniciar.disabled) botaoIniciar.click(); });

atualizar();
setInterval(atualizar, 2000);
