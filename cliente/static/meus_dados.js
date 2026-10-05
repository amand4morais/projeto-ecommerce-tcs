const listaDados = document.getElementById("lista-dados");
const dicaDados = document.getElementById("dica-dados");
const botaoConsultar = document.getElementById("botao-consultar");
const formEditar = document.getElementById("form-editar");
const botaoExcluir = document.getElementById("botao-excluir");
const dialogoExclusao = document.getElementById("dialogo-exclusao");
const botaoCancelarExclusao = document.getElementById("botao-cancelar-exclusao");
const botaoConfirmarExclusao = document.getElementById("botao-confirmar-exclusao");

function caminhoDoUsuario() {
  const id = obterSessao()?.usuario?.id;
  if (id === undefined || id === null || String(id) === "") return null;
  return `/users/${encodeURIComponent(String(id))}`;
}

function semIdDoUsuario() {
  mostrarMensagem("O servidor não informou o id do usuário no login, então não é possível acessar o cadastro.", "erro");
}

function prepararMeusDados() {
  const usuario = obterSessao()?.usuario ?? {};
  listaDados.replaceChildren();
  dicaDados.hidden = false;
  formEditar.reset();
  formEditar.elements.nome.value = usuario.nome ?? "";
  formEditar.elements.email.value = usuario.email ?? "";
}

function exibirDados(usuario) {
  listaDados.replaceChildren();
  for (const [rotulo, valor] of [["Id", usuario?.id], ["Nome", usuario?.nome], ["E-mail", usuario?.email]]) {
    listaDados.append(criarElemento("dt", null, rotulo), criarElemento("dd", null, valor ?? "—"));
  }
  dicaDados.hidden = true;
}

function atualizarUsuarioDaSessao(usuario) {
  const sessao = obterSessao();
  if (!sessao || !usuario || typeof usuario !== "object") return;
  sessao.usuario = { ...sessao.usuario, ...usuario };
  salvarSessao(sessao);
  exibirTela();
}

async function consultarDados() {
  const caminho = caminhoDoUsuario();
  if (!caminho) return semIdDoUsuario();
  const resposta = await enviarRequisicao("GET", caminho, undefined, true);
  if (resposta.ok) {
    exibirDados(resposta.corpo);
    mostrarMensagem("Dados consultados.", "sucesso");
  } else if (resposta.status !== 401) {
    mostrarMensagem(resposta.mensagem, "erro");
  }
}

async function salvarAlteracoes(evento) {
  evento.preventDefault();
  const caminho = caminhoDoUsuario();
  if (!caminho) return semIdDoUsuario();

  const atual = obterSessao().usuario ?? {};
  const campos = lerCampos(formEditar, ["nome", "email", "senha"]);
  const corpo = {};
  if (campos.nome !== (atual.nome ?? "")) corpo.nome = campos.nome;
  if (campos.email !== (atual.email ?? "")) corpo.email = campos.email;
  if (campos.senha !== "") corpo.senha = campos.senha;
  if (Object.keys(corpo).length === 0) {
    mostrarMensagem("Nenhuma alteração para enviar.");
    return;
  }

  const resposta = await enviarRequisicao("PATCH", caminho, corpo, true);
  if (resposta.ok) {
    atualizarUsuarioDaSessao(resposta.corpo);
    exibirDados(resposta.corpo);
    formEditar.elements.senha.value = "";
    mostrarMensagem("Dados atualizados.", "sucesso");
  } else if (resposta.status !== 401) {
    mostrarMensagem(resposta.mensagem, "erro");
  }
}

async function excluirConta() {
  const caminho = caminhoDoUsuario();
  if (!caminho) {
    dialogoExclusao.close();
    return semIdDoUsuario();
  }
  const resposta = await enviarRequisicao("DELETE", caminho, undefined, true);
  dialogoExclusao.close();
  if (resposta.ok) {
    limparSessao();
    exibirTela();
    mostrarMensagem("Conta excluída.", "sucesso");
  } else if (resposta.status !== 401) {
    mostrarMensagem(resposta.mensagem, "erro");
  }
}

botaoConsultar.addEventListener("click", () => comBotaoOcupado(botaoConsultar, consultarDados));
formEditar.addEventListener("submit", (e) => comBotaoOcupado(e.submitter ?? formEditar.querySelector("button"), () => salvarAlteracoes(e)));
botaoExcluir.addEventListener("click", () => dialogoExclusao.showModal());
botaoCancelarExclusao.addEventListener("click", () => dialogoExclusao.close());
botaoConfirmarExclusao.addEventListener("click", () => comBotaoOcupado(botaoConfirmarExclusao, excluirConta));
document.addEventListener("sessao-iniciada", prepararMeusDados);

prepararMeusDados();
