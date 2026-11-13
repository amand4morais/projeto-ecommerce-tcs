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
  dicaDados.textContent = "O servidor não informou o id do usuário no login, então não é possível acessar o cadastro.";
  mostrarMensagem(dicaDados.textContent, "erro");
}

function preencherFormulario() {
  const usuario = obterSessao()?.usuario ?? {};
  formEditar.elements.nome.value = usuario.nome ?? "";
  formEditar.elements.email.value = usuario.email ?? "";
  formEditar.elements.senha.value = "";
}

function exibirDados(usuario) {
  listaDados.replaceChildren();
  const papel = usuario?.admin === true ? "Administrador" : "Usuário comum";
  for (const [rotulo, valor] of [["Id", usuario?.id], ["Nome", usuario?.nome], ["E-mail", usuario?.email], ["Papel", papel]]) {
    listaDados.append(criarElemento("dt", null, rotulo), criarElemento("dd", null, valor ?? "—"));
  }
  dicaDados.hidden = true;
}

function atualizarUsuarioDaSessao(usuario) {
  const sessao = obterSessao();
  if (!sessao || !usuario || typeof usuario !== "object") return;
  sessao.usuario = { ...sessao.usuario, ...usuario, admin: sessao.usuario?.admin === true };
  salvarSessao(sessao);
  exibirIdentidade();
  preencherFormulario();
}

async function consultarDados(avisar) {
  const caminho = caminhoDoUsuario();
  if (!caminho) return semIdDoUsuario();
  const resposta = await enviarRequisicao("GET", caminho, undefined, true);
  if (resposta.ok) {
    exibirDados(resposta.corpo);
    if (avisar) mostrarMensagem("Dados atualizados a partir do servidor.", "sucesso");
  } else if (resposta.status !== 401) {
    dicaDados.textContent = "Não foi possível carregar seus dados.";
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
    irPara("/", "Conta excluída.");
  } else if (resposta.status !== 401) {
    mostrarMensagem(resposta.mensagem, "erro");
  }
}

botaoConsultar.addEventListener("click", () => comBotaoOcupado(botaoConsultar, () => consultarDados(true)));
formEditar.addEventListener("submit", (e) => comBotaoOcupado(e.submitter ?? formEditar.querySelector("button"), () => salvarAlteracoes(e)));
botaoExcluir.addEventListener("click", () => dialogoExclusao.showModal());
botaoCancelarExclusao.addEventListener("click", () => dialogoExclusao.close());
botaoConfirmarExclusao.addEventListener("click", () => comBotaoOcupado(botaoConfirmarExclusao, excluirConta));

if (paginaLiberada) {
  preencherFormulario();
  consultarDados(false);
}
