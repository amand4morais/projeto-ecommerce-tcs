const CHAVE_SESSAO = "sessao";
const CHAVE_CONEXAO = "conexao";
const MENSAGENS_PADRAO = {
  400: "Requisição inválida.",
  401: "Sessão inválida ou expirada. Faça login novamente.",
  403: "Acesso negado.",
  404: "Recurso não encontrado.",
  405: "Operação não suportada pelo servidor.",
  409: "Conflito com dados já existentes.",
  500: "Erro interno do servidor.",
};

const campoHost = document.getElementById("host");
const campoPorta = document.getElementById("porta");
const listaComunicacao = document.getElementById("lista-comunicacao");

function obterSessao() {
  try {
    return JSON.parse(sessionStorage.getItem(CHAVE_SESSAO));
  } catch {
    return null;
  }
}

function salvarSessao(sessao) {
  sessionStorage.setItem(CHAVE_SESSAO, JSON.stringify(sessao));
}

function limparSessao() {
  sessionStorage.removeItem(CHAVE_SESSAO);
}

function obterConexao() {
  try {
    return JSON.parse(sessionStorage.getItem(CHAVE_CONEXAO));
  } catch {
    return null;
  }
}

function salvarConexao(conexao) {
  sessionStorage.setItem(CHAVE_CONEXAO, JSON.stringify(conexao));
}

function limparConexao() {
  sessionStorage.removeItem(CHAVE_CONEXAO);
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
  if (texto !== undefined) elemento.textContent = texto;
  return elemento;
}

function formatarCorpo(corpo) {
  if (typeof corpo === "string") return corpo;
  const exibido = typeof corpo?.token === "string" ? { ...corpo, token: mascararToken(corpo.token) } : corpo;
  return JSON.stringify(exibido, null, 2);
}

function registrarEnvio(metodo, url, corpo, token) {
  const vazio = listaComunicacao.querySelector(".vazio");
  if (vazio) vazio.remove();

  const entrada = criarElemento("li", "entrada");
  const titulo = criarElemento("div", "linha-titulo");
  titulo.append(
    criarElemento("span", "hora", new Date().toLocaleTimeString("pt-BR")),
    criarElemento("span", "seta-envio", `→ ${metodo}`),
    criarElemento("span", null, url),
  );
  entrada.append(titulo);

  const detalhes = [];
  if (token) detalhes.push(`Authorization: Bearer ${mascararToken(token)}`);
  if (corpo !== undefined) detalhes.push(formatarCorpo(corpo));
  if (detalhes.length) entrada.append(criarElemento("pre", "corpo", detalhes.join("\n\n")));

  const aguardando = criarElemento("p", "aguardando", "Aguardando resposta…");
  entrada.append(aguardando);
  listaComunicacao.prepend(entrada);
  return aguardando;
}

function registrarResposta(marcador, status, conteudo) {
  const bloco = document.createElement("div");
  const sucesso = status !== null && status >= 200 && status < 300;
  const titulo = criarElemento("div", "linha-titulo");
  titulo.append(criarElemento("span", `seta-resposta ${sucesso ? "sucesso" : "falha"}`, status === null ? "✕ Falha" : `← ${status}`));
  bloco.append(titulo);
  if (conteudo !== null && conteudo !== "") bloco.append(criarElemento("pre", "corpo", formatarCorpo(conteudo)));
  marcador.replaceWith(bloco);
}

async function enviarRequisicao(metodo, caminho, corpo, usarToken = false) {
  const host = campoHost.value.trim();
  const porta = campoPorta.value.trim();
  const token = usarToken ? obterSessao()?.token : undefined;
  const marcador = registrarEnvio(metodo, `http://${host}:${porta}/api/v1${caminho}`, corpo, token);

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
    registrarResposta(marcador, null, dados.mensagem);
    return { ok: false, status: null, corpo: null, mensagem: dados.mensagem };
  }

  registrarResposta(marcador, dados.status, dados.corpo ?? dados.texto);
  const ok = dados.status >= 200 && dados.status < 300;
  if (dados.status === 401 && token) {
    limparSessao();
    document.dispatchEvent(new CustomEvent("sessao-encerrada"));
  }
  return { ok, status: dados.status, corpo: dados.corpo, mensagem: ok ? null : mensagemDaResposta(dados.status, dados.corpo) };
}

document.getElementById("botao-limpar").addEventListener("click", () => {
  listaComunicacao.replaceChildren(criarElemento("li", "vazio", "Nenhuma requisição enviada ainda."));
});
