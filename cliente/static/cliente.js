const CHAVE_SESSAO = "sessao";
const CHAVE_CONEXAO = "conexao";
const CHAVE_COMUNICACAO = "comunicacao";
const CHAVE_AVISO = "aviso";
const LIMITE_COMUNICACAO = 100;
const MENSAGENS_PADRAO = {
  400: "Requisição inválida.",
  401: "Sessão inválida ou expirada. Faça login novamente.",
  403: "Acesso negado.",
  404: "Recurso não encontrado.",
  405: "Operação não suportada pelo servidor.",
  409: "Conflito com dados já existentes.",
  500: "Erro interno do servidor.",
};

const elementoMensagem = document.getElementById("mensagem");
const listaComunicacao = document.getElementById("lista-comunicacao");
const gaveta = document.getElementById("gaveta");
const botaoComunicacao = document.getElementById("botao-comunicacao");
const botaoSair = document.getElementById("botao-sair");

function lerArmazenado(chave) {
  try {
    return JSON.parse(sessionStorage.getItem(chave));
  } catch {
    return null;
  }
}

function salvarArmazenado(chave, valor) {
  try {
    sessionStorage.setItem(chave, JSON.stringify(valor));
  } catch {
    // Armazenamento indisponível: a página continua funcionando, só não lembra entre recarregamentos.
  }
}

function removerArmazenado(chave) {
  try {
    sessionStorage.removeItem(chave);
  } catch {
    // Armazenamento indisponível: nada a remover.
  }
}

const obterSessao = () => lerArmazenado(CHAVE_SESSAO);
const salvarSessao = (sessao) => salvarArmazenado(CHAVE_SESSAO, sessao);
const limparSessao = () => removerArmazenado(CHAVE_SESSAO);
const obterConexao = () => lerArmazenado(CHAVE_CONEXAO);
const salvarConexao = (conexao) => salvarArmazenado(CHAVE_CONEXAO, conexao);
const limparConexao = () => removerArmazenado(CHAVE_CONEXAO);

function definirAviso(texto, tipo) {
  salvarArmazenado(CHAVE_AVISO, { texto, tipo });
}

function irPara(caminho, aviso, tipo = "sucesso") {
  if (aviso) definirAviso(aviso, tipo);
  window.location.href = caminho;
}

function mostrarMensagem(texto, tipo = "") {
  elementoMensagem.textContent = texto;
  elementoMensagem.dataset.tipo = tipo;
}

function mensagemDaResposta(status, corpo) {
  if (corpo && typeof corpo.mensagem === "string") return corpo.mensagem;
  return MENSAGENS_PADRAO[status] || `O servidor respondeu com status ${status}.`;
}

function mascararToken(token) {
  return token.length > 10 ? `${token.slice(0, 4)}…${token.slice(-4)}` : "***";
}

function criarElemento(tag, classe, texto) {
  const elemento = document.createElement(tag);
  if (classe) elemento.className = classe;
  if (texto !== undefined && texto !== null) elemento.textContent = texto;
  return elemento;
}

function formatarCorpo(corpo) {
  if (typeof corpo === "string") return corpo;
  const exibido = typeof corpo?.token === "string" ? { ...corpo, token: mascararToken(corpo.token) } : corpo;
  return JSON.stringify(exibido, null, 2);
}

async function comBotaoOcupado(botao, acao) {
  botao.disabled = true;
  try {
    await acao();
  } finally {
    botao.disabled = false;
  }
}

function lerCampos(formulario, nomes) {
  const dados = new FormData(formulario);
  return Object.fromEntries(nomes.map((nome) => [nome, dados.get(nome)]));
}

function lerHistorico() {
  const historico = lerArmazenado(CHAVE_COMUNICACAO);
  return Array.isArray(historico) ? historico : [];
}

function salvarHistorico(historico) {
  salvarArmazenado(CHAVE_COMUNICACAO, historico.slice(-LIMITE_COMUNICACAO));
}

function entradaDaComunicacao(item) {
  const entrada = criarElemento("li", "entrada");
  const titulo = criarElemento("div", "entrada-titulo");
  titulo.append(
    criarElemento("span", "hora", item.hora),
    criarElemento("span", `metodo metodo-${item.metodo.toLowerCase()}`, item.metodo),
    criarElemento("span", "caminho", item.url),
  );
  entrada.append(titulo);
  entrada.append(criarElemento("p", "rotulo", "Enviado"), criarElemento("pre", "corpo", item.envio || "(sem corpo)"));

  if (item.pendente) {
    entrada.append(criarElemento("p", "aguardando", "Aguardando resposta…"));
    return entrada;
  }
  const sucesso = item.status !== null && item.status >= 200 && item.status < 300;
  const rotulo = criarElemento("p", "rotulo");
  rotulo.append("Recebido ", criarElemento("span", `status ${sucesso ? "status-ok" : item.status === null ? "status-falha" : "status-erro"}`, item.status === null ? "✕ Falha" : item.status));
  entrada.append(rotulo, criarElemento("pre", "corpo", item.resposta || "(sem corpo)"));
  return entrada;
}

function exibirComunicacao() {
  const historico = lerHistorico();
  document.getElementById("contador-comunicacao").textContent = historico.length;
  if (historico.length === 0) {
    listaComunicacao.replaceChildren(criarElemento("li", "vazio", "Nenhuma requisição enviada ainda."));
    return;
  }
  listaComunicacao.replaceChildren(...historico.slice().reverse().map(entradaDaComunicacao));
}

function registrarEnvio(metodo, url, corpo, token) {
  const envio = [token ? `Authorization: Bearer ${mascararToken(token)}` : null, corpo !== undefined ? formatarCorpo(corpo) : null]
    .filter(Boolean)
    .join("\n\n");
  const item = { id: `${Date.now()}-${Math.random()}`, hora: new Date().toLocaleTimeString("pt-BR"), metodo, url, envio, pendente: true };
  const historico = lerHistorico();
  historico.push(item);
  salvarHistorico(historico);
  exibirComunicacao();
  return item.id;
}

function registrarResposta(id, status, conteudo) {
  const historico = lerHistorico();
  const item = historico.find((registro) => registro.id === id);
  if (!item) return;
  item.pendente = false;
  item.status = status;
  item.resposta = conteudo === null || conteudo === undefined || conteudo === "" ? "" : formatarCorpo(conteudo);
  salvarHistorico(historico);
  exibirComunicacao();
}

async function enviarRequisicao(metodo, caminho, corpo, usarToken = false, destino = obterConexao()) {
  const host = destino?.host ?? "";
  const porta = destino?.porta ?? "";
  const token = usarToken ? obterSessao()?.token : undefined;
  const id = registrarEnvio(metodo, `http://${host}:${porta}/api/v1${caminho}`, corpo, token);

  let dados;
  let respostaLocalOk = false;
  try {
    const resposta = await fetch("/enviar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ host, porta, metodo, caminho, corpo, token }),
    });
    respostaLocalOk = resposta.ok;
    dados = await resposta.json();
  } catch {
    dados = { mensagem: "O cliente local não respondeu. Ele ainda está rodando no terminal?" };
  }

  if (!respostaLocalOk) {
    registrarResposta(id, null, dados.mensagem);
    return { ok: false, status: null, corpo: null, mensagem: dados.mensagem };
  }

  registrarResposta(id, dados.status, dados.corpo ?? dados.texto);
  const ok = dados.status >= 200 && dados.status < 300;
  if (dados.status === 401 && token) {
    limparSessao();
    irPara("/", "Sua sessão não é mais válida neste servidor. Entre novamente.", "erro");
  }
  return { ok, status: dados.status, corpo: dados.corpo, mensagem: ok ? null : mensagemDaResposta(dados.status, dados.corpo) };
}

function exibirIdentidade() {
  const sessao = obterSessao();
  const conexao = obterConexao();
  document.getElementById("selo-conexao").hidden = !conexao;
  document.getElementById("texto-conexao").textContent = conexao ? `${conexao.host}:${conexao.porta}` : "";
  document.getElementById("selo-usuario").hidden = !sessao;
  document.getElementById("texto-usuario").textContent = sessao?.usuario?.nome ?? sessao?.usuario?.email ?? "";
  document.getElementById("etiqueta-adm").hidden = sessao?.usuario?.admin !== true;
  document.getElementById("menu").hidden = !sessao;
  document.getElementById("menu-usuarios").hidden = sessao?.usuario?.admin !== true;
  botaoSair.hidden = !sessao;
}

function abrirGaveta(abrir) {
  gaveta.hidden = !abrir;
  botaoComunicacao.setAttribute("aria-expanded", String(abrir));
  if (abrir) gaveta.focus();
}

async function sair() {
  const sessao = obterSessao();
  if (!sessao) return irPara("/");
  const resposta = await enviarRequisicao("DELETE", `/sessions/${encodeURIComponent(sessao.id)}`, undefined, true);
  if (resposta.ok) {
    limparSessao();
    irPara("/", "Você saiu da conta.");
  } else if (resposta.status !== 401) {
    mostrarMensagem(resposta.mensagem, "erro");
  }
}

function protegerPagina() {
  const exigeSessao = document.body.dataset.exigeSessao === "sim";
  if (exigeSessao && !obterSessao()) {
    irPara("/", "Entre na sua conta para acessar esta página.", "erro");
    return false;
  }
  if (document.body.dataset.exigeAdmin === "sim" && obterSessao()?.usuario?.admin !== true) {
    irPara("/conta", "Esta página é exclusiva para administradores.", "erro");
    return false;
  }
  if (!exigeSessao && obterSessao()) {
    irPara("/conta");
    return false;
  }
  return true;
}

function exibirAvisoPendente() {
  const aviso = lerArmazenado(CHAVE_AVISO);
  removerArmazenado(CHAVE_AVISO);
  if (aviso?.texto) mostrarMensagem(aviso.texto, aviso.tipo);
}

gaveta.tabIndex = -1;
botaoComunicacao.addEventListener("click", () => abrirGaveta(gaveta.hidden));
document.getElementById("botao-fechar-gaveta").addEventListener("click", () => abrirGaveta(false));
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !gaveta.hidden) abrirGaveta(false); });
document.getElementById("botao-limpar").addEventListener("click", () => {
  salvarHistorico([]);
  exibirComunicacao();
});
botaoSair.addEventListener("click", () => comBotaoOcupado(botaoSair, sair));

const paginaLiberada = protegerPagina();
exibirIdentidade();
exibirComunicacao();
if (paginaLiberada) exibirAvisoPendente();
