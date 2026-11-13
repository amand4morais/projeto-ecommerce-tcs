const campoPorta = document.getElementById("porta");
const botaoIniciar = document.getElementById("botao-iniciar");
const botaoParar = document.getElementById("botao-parar");
const mensagem = document.getElementById("mensagem");
const listaEnderecos = document.getElementById("lista-enderecos");
const linhasLogados = document.getElementById("linhas-logados");
const erroLogados = document.getElementById("erro-logados");

let portaAtual = null;
let enderecosAtuais = [];

function mostrarMensagem(texto, ehErro) {
  mensagem.textContent = texto;
  mensagem.classList.toggle("erro", Boolean(ehErro));
}

function aplicarEstado(estado) {
  campoPorta.disabled = estado.rodando;
  botaoIniciar.disabled = estado.rodando;
  botaoParar.disabled = !estado.rodando;
  if (estado.rodando) campoPorta.value = estado.porta;
  portaAtual = estado.rodando ? estado.porta : null;
  exibirEnderecos();
}

function exibirEnderecos() {
  listaEnderecos.replaceChildren();
  if (enderecosAtuais.length === 0) {
    listaEnderecos.append(criarElemento("li", "apagado", "IP não identificado. Consulte com ipconfig."));
    return;
  }
  for (const ip of enderecosAtuais) {
    const item = criarElemento("li", "endereco");
    item.append(criarElemento("span", "endereco-ip", ip), criarElemento("span", "endereco-porta", portaAtual ? `: ${portaAtual}` : ": porta"));
    listaEnderecos.append(item);
  }
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
    atualizarEstadoApi();
  } catch {
    mostrarMensagem("Não foi possível falar com o painel. Ele ainda está rodando no terminal?", true);
  }
}

function formatarLogin(iso) {
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? "—" : data.toLocaleString("pt-BR");
}

function exibirLogados(usuarios) {
  linhasLogados.replaceChildren();
  if (usuarios.length === 0) {
    const linha = criarElemento("tr", "vazio");
    const celula = criarElemento("td", null, "Nenhum usuário logado no momento.");
    celula.colSpan = 6;
    linha.append(celula);
    linhasLogados.append(linha);
    return;
  }
  for (const u of usuarios) {
    const linha = document.createElement("tr");
    const papel = criarElemento("td");
    papel.append(criarElemento("span", u.admin ? "etiqueta etiqueta-adm" : "etiqueta etiqueta-comum", u.admin ? "ADM" : "Comum"));
    linha.append(
      criarElemento("td", "destaque", u.nome),
      criarElemento("td", null, u.email),
      papel,
      criarElemento("td", "dados", u.sessoes),
      criarElemento("td", "dados", u.ip || "—"),
      criarElemento("td", "dados", formatarLogin(u.ultimo_login)),
    );
    linhasLogados.append(linha);
  }
}

async function atualizarPainel() {
  try {
    const [respostaLogados, indicadores] = await Promise.all([fetch("/usuarios-logados"), buscarJSON("/indicadores")]);
    const logados = await respostaLogados.json();
    if (respostaLogados.ok) {
      erroLogados.hidden = true;
      exibirLogados(logados);
      document.getElementById("ind-usuarios").textContent = logados.length;
      document.getElementById("ind-sessoes").textContent = logados.reduce((soma, u) => soma + u.sessoes, 0);
    } else {
      erroLogados.hidden = false;
      erroLogados.textContent = logados.mensagem;
    }
    document.getElementById("ind-clientes").textContent = indicadores.clientes_ativos;
    document.getElementById("ind-requisicoes").textContent = indicadores.requisicoes;
    if (JSON.stringify(indicadores.enderecos) !== JSON.stringify(enderecosAtuais)) {
      enderecosAtuais = indicadores.enderecos;
      exibirEnderecos();
    }
  } catch {
    // Painel fora do ar: tenta de novo no próximo ciclo.
  }
}

document.addEventListener("estado-api", (evento) => aplicarEstado(evento.detail));
botaoIniciar.addEventListener("click", () => enviar("/iniciar", { porta: campoPorta.value }));
botaoParar.addEventListener("click", () => enviar("/parar"));
campoPorta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !botaoIniciar.disabled) botaoIniciar.click(); });

exibirEnderecos();
atualizarPainel();
setInterval(atualizarPainel, 2000);
