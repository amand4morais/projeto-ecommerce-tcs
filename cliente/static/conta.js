const telaVisitante = document.getElementById("tela-visitante");
const telaLogado = document.getElementById("tela-logado");
const abaEntrar = document.getElementById("aba-entrar");
const abaCadastro = document.getElementById("aba-cadastro");
const formEntrar = document.getElementById("form-entrar");
const formCadastro = document.getElementById("form-cadastro");
const botaoSair = document.getElementById("botao-sair");
const mensagemConta = document.getElementById("mensagem-conta");
const avisoConexao = document.getElementById("aviso-conexao");
const botaoConectar = document.getElementById("botao-conectar");
const botaoDesconectar = document.getElementById("botao-desconectar");
const estadoConexao = document.getElementById("estado-conexao");

function mostrarMensagem(texto, tipo = "") {
  mensagemConta.textContent = texto;
  mensagemConta.dataset.tipo = tipo;
}

function selecionarAba(aba) {
  const entrar = aba === "entrar";
  abaEntrar.setAttribute("aria-selected", String(entrar));
  abaCadastro.setAttribute("aria-selected", String(!entrar));
  formEntrar.hidden = !entrar;
  formCadastro.hidden = entrar;
}

function exibirTela() {
  const sessao = obterSessao();
  if (sessao && !obterConexao()) salvarConexao({ host: sessao.host, porta: sessao.porta });
  const conexao = obterConexao();
  const conectado = Boolean(conexao);
  const logado = Boolean(sessao);

  campoHost.disabled = conectado;
  campoPorta.disabled = conectado;
  botaoConectar.hidden = conectado;
  botaoDesconectar.hidden = !conectado;
  botaoDesconectar.disabled = logado;
  botaoDesconectar.title = logado ? "Saia da conta antes de desconectar." : "";
  estadoConexao.textContent = conectado ? `Conectado a ${conexao.host}:${conexao.porta}` : "";

  avisoConexao.hidden = conectado;
  telaVisitante.hidden = !conectado || logado;
  telaLogado.hidden = !logado;

  if (conectado) {
    campoHost.value = conexao.host;
    campoPorta.value = conexao.porta;
  }
  if (logado) {
    document.getElementById("nome-logado").textContent = sessao.usuario?.nome ?? "";
    document.getElementById("email-logado").textContent = sessao.usuario?.email ? `(${sessao.usuario.email})` : "";
  }
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

async function conectar() {
  const resposta = await enviarRequisicao("OPTIONS", "/users");
  if (resposta.status === null) {
    mostrarMensagem(resposta.mensagem, "erro");
    return;
  }
  salvarConexao({ host: campoHost.value.trim(), porta: campoPorta.value.trim() });
  exibirTela();
  if (resposta.ok) {
    mostrarMensagem("Servidor encontrado. Agora você pode entrar ou criar uma conta.", "sucesso");
  } else {
    mostrarMensagem(`O servidor respondeu, mas com status ${resposta.status} ao teste de conexão. Ele pode não seguir o protocolo.`, "erro");
  }
}

function desconectar() {
  limparConexao();
  exibirTela();
  mostrarMensagem("");
}

async function criarConta(evento) {
  evento.preventDefault();
  const corpo = lerCampos(formCadastro, ["nome", "email", "senha"]);
  const resposta = await enviarRequisicao("POST", "/users", corpo);
  if (!resposta.ok) {
    mostrarMensagem(resposta.mensagem, "erro");
    return;
  }
  formCadastro.reset();
  selecionarAba("entrar");
  formEntrar.elements.email.value = corpo.email;
  mostrarMensagem("Conta criada! Agora é só entrar.", "sucesso");
}

async function entrar(evento) {
  evento.preventDefault();
  const corpo = lerCampos(formEntrar, ["email", "senha"]);
  const resposta = await enviarRequisicao("POST", "/sessions", corpo);
  if (!resposta.ok) {
    mostrarMensagem(resposta.mensagem, "erro");
    return;
  }
  const dados = resposta.corpo;
  if (!dados || typeof dados.token !== "string" || dados.id === undefined || dados.id === null) {
    mostrarMensagem("O servidor respondeu ao login sem o id da sessão ou o token.", "erro");
    return;
  }
  salvarSessao({
    id: String(dados.id),
    token: dados.token,
    usuario: dados.usuario ?? { email: corpo.email },
    host: obterConexao().host,
    porta: obterConexao().porta,
  });
  formEntrar.reset();
  mostrarMensagem("");
  exibirTela();
}

async function sair() {
  const sessao = obterSessao();
  if (!sessao) {
    exibirTela();
    return;
  }
  const resposta = await enviarRequisicao("DELETE", `/sessions/${encodeURIComponent(sessao.id)}`, undefined, true);
  if (resposta.ok) {
    limparSessao();
    exibirTela();
    mostrarMensagem("Você saiu da conta.", "sucesso");
  } else if (resposta.status !== 401) {
    mostrarMensagem(resposta.mensagem, "erro");
  }
}

abaEntrar.addEventListener("click", () => { selecionarAba("entrar"); mostrarMensagem(""); });
abaCadastro.addEventListener("click", () => { selecionarAba("cadastro"); mostrarMensagem(""); });
formCadastro.addEventListener("submit", (e) => comBotaoOcupado(e.submitter ?? formCadastro.querySelector("button"), () => criarConta(e)));
formEntrar.addEventListener("submit", (e) => comBotaoOcupado(e.submitter ?? formEntrar.querySelector("button"), () => entrar(e)));
botaoSair.addEventListener("click", () => comBotaoOcupado(botaoSair, sair));
botaoConectar.addEventListener("click", () => comBotaoOcupado(botaoConectar, conectar));
botaoDesconectar.addEventListener("click", desconectar);
for (const campo of [campoHost, campoPorta]) {
  campo.addEventListener("keydown", (e) => { if (e.key === "Enter" && !botaoConectar.disabled) botaoConectar.click(); });
}
document.addEventListener("sessao-encerrada", () => {
  exibirTela();
  mostrarMensagem("Sua sessão não é mais válida neste servidor. Entre novamente.", "erro");
});

exibirTela();
