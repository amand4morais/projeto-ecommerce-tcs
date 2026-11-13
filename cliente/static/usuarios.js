const linhasUsuarios = document.getElementById("linhas-usuarios");
const dicaLista = document.getElementById("dica-lista");
const areaTabela = document.getElementById("area-tabela");
const botaoAtualizarLista = document.getElementById("botao-atualizar-lista");
const idSelecionado = document.getElementById("id-selecionado");
const detalheVazio = document.getElementById("detalhe-vazio");
const detalheVer = document.getElementById("detalhe-ver");
const dadosSelecionado = document.getElementById("dados-selecionado");
const formEditarUsuario = document.getElementById("form-editar-usuario");
const dialogoExclusao = document.getElementById("dialogo-exclusao-usuario");
const botaoConfirmarExclusao = document.getElementById("botao-confirmar-exclusao-usuario");

let usuarios = [];
let selecionado = null;
let idParaExcluir = null;

const caminhoDoUsuario = (id) => `/users/${encodeURIComponent(String(id))}`;
const ehMinhaConta = (id) => String(id) === String(obterSessao()?.usuario?.id);

function etiquetaPapel(admin) {
  return criarElemento("span", admin === true ? "etiqueta etiqueta-adm" : "etiqueta etiqueta-comum", admin === true ? "ADM" : "Comum");
}

function botaoDeLinha(texto, classe, acao, usuario) {
  const botao = criarElemento("button", `botao botao-pequeno ${classe}`, texto);
  botao.type = "button";
  botao.setAttribute("aria-label", `${texto} ${usuario.nome ?? usuario.email ?? usuario.id}`);
  botao.addEventListener("click", () => comBotaoOcupado(botao, () => acao(usuario.id)));
  return botao;
}

function exibirLista() {
  linhasUsuarios.replaceChildren();
  areaTabela.hidden = usuarios.length === 0;
  dicaLista.hidden = usuarios.length > 0;
  if (usuarios.length === 0) dicaLista.textContent = "Nenhum usuário cadastrado neste servidor.";
  for (const usuario of usuarios) {
    const linha = document.createElement("tr");
    if (selecionado && String(selecionado.id) === String(usuario.id)) linha.className = "linha-selecionada";
    const papel = criarElemento("td");
    papel.append(etiquetaPapel(usuario.admin));
    const acoes = criarElemento("td", "celula-acoes");
    acoes.append(
      botaoDeLinha("Ver", "botao-secundario", verUsuario, usuario),
      botaoDeLinha("Editar", "botao-secundario", editarUsuario, usuario),
      botaoDeLinha("Excluir", "botao-perigo", pedirExclusao, usuario),
    );
    linha.append(criarElemento("td", "dados", usuario.id), criarElemento("td", "destaque", usuario.nome ?? "—"), criarElemento("td", "dados", usuario.email ?? "—"), papel, acoes);
    linhasUsuarios.append(linha);
  }
}

function exibirDetalhe(modo) {
  detalheVazio.hidden = selecionado !== null;
  detalheVer.hidden = !selecionado || modo !== "ver";
  formEditarUsuario.hidden = !selecionado || modo !== "editar";
  idSelecionado.textContent = selecionado ? `Id ${selecionado.id}` : "";
  if (!selecionado) return;

  dadosSelecionado.replaceChildren();
  const papel = selecionado.admin === true ? "Administrador" : "Usuário comum";
  for (const [rotulo, valor] of [["Id", selecionado.id], ["Nome", selecionado.nome], ["E-mail", selecionado.email], ["Papel", papel]]) {
    dadosSelecionado.append(criarElemento("dt", null, rotulo), criarElemento("dd", null, valor ?? "—"));
  }
  if (modo === "editar") {
    formEditarUsuario.elements.nome.value = selecionado.nome ?? "";
    formEditarUsuario.elements.email.value = selecionado.email ?? "";
    formEditarUsuario.elements.senha.value = "";
    formEditarUsuario.elements.nome.focus();
  }
  exibirLista();
}

function limparSelecao() {
  selecionado = null;
  exibirDetalhe("ver");
}

async function carregarLista(avisar) {
  const resposta = await enviarRequisicao("GET", "/users", undefined, true);
  if (resposta.status === 401) return;
  if (!resposta.ok) {
    dicaLista.textContent = "Não foi possível carregar a lista de usuários.";
    mostrarMensagem(resposta.mensagem, "erro");
    return;
  }
  if (!Array.isArray(resposta.corpo)) {
    dicaLista.textContent = "O servidor respondeu à listagem em um formato inesperado.";
    mostrarMensagem(dicaLista.textContent, "erro");
    return;
  }
  usuarios = resposta.corpo;
  if (selecionado && !usuarios.some((u) => String(u.id) === String(selecionado.id))) limparSelecao();
  exibirLista();
  if (avisar) mostrarMensagem("Lista de usuários atualizada.", "sucesso");
}

async function tratarFalha(resposta) {
  if (resposta.status === 401) return;
  mostrarMensagem(resposta.mensagem, "erro");
  if (resposta.status === 404) await carregarLista(false);
}

async function buscarUsuario(id) {
  const resposta = await enviarRequisicao("GET", caminhoDoUsuario(id), undefined, true);
  if (!resposta.ok) {
    await tratarFalha(resposta);
    return false;
  }
  selecionado = resposta.corpo && typeof resposta.corpo === "object" ? resposta.corpo : { id };
  return true;
}

async function verUsuario(id) {
  if (await buscarUsuario(id)) {
    exibirDetalhe("ver");
    mostrarMensagem(`Dados de ${selecionado.nome ?? selecionado.email ?? `id ${id}`} consultados no servidor.`, "sucesso");
  }
}

async function editarUsuario(id) {
  if (!selecionado || String(selecionado.id) !== String(id)) {
    if (!(await buscarUsuario(id))) return;
  }
  exibirDetalhe("editar");
  mostrarMensagem("");
}

function atualizarListaLocal(usuario) {
  usuarios = usuarios.map((u) => (String(u.id) === String(usuario.id) ? { ...u, ...usuario } : u));
}

function atualizarMinhaSessao(usuario) {
  const sessao = obterSessao();
  if (!sessao) return;
  sessao.usuario = { ...sessao.usuario, nome: usuario.nome, email: usuario.email };
  salvarSessao(sessao);
  exibirIdentidade();
}

async function salvarEdicao(evento) {
  evento.preventDefault();
  const campos = lerCampos(formEditarUsuario, ["nome", "email", "senha"]);
  const corpo = {};
  if (campos.nome !== (selecionado.nome ?? "")) corpo.nome = campos.nome;
  if (campos.email !== (selecionado.email ?? "")) corpo.email = campos.email;
  if (campos.senha !== "") corpo.senha = campos.senha;
  if (Object.keys(corpo).length === 0) {
    mostrarMensagem("Nenhuma alteração para enviar.");
    return;
  }
  const resposta = await enviarRequisicao("PATCH", caminhoDoUsuario(selecionado.id), corpo, true);
  if (!resposta.ok) {
    await tratarFalha(resposta);
    return;
  }
  const atualizado = resposta.corpo && typeof resposta.corpo === "object" ? resposta.corpo : { ...selecionado, ...corpo };
  selecionado = { ...selecionado, ...atualizado };
  atualizarListaLocal(selecionado);
  if (ehMinhaConta(selecionado.id)) atualizarMinhaSessao(selecionado);
  exibirDetalhe("ver");
  mostrarMensagem("Usuário atualizado.", "sucesso");
}

function pedirExclusao(id) {
  const usuario = usuarios.find((u) => String(u.id) === String(id)) ?? selecionado ?? { id };
  idParaExcluir = id;
  document.getElementById("texto-exclusao-usuario").textContent =
    `O cadastro de ${usuario.nome ?? usuario.email ?? `id ${id}`} será removido deste servidor, junto com todas as sessões dele. Esta ação não pode ser desfeita.`;
  document.getElementById("aviso-propria-conta").hidden = !ehMinhaConta(id);
  dialogoExclusao.showModal();
}

async function confirmarExclusao() {
  const id = idParaExcluir;
  const resposta = await enviarRequisicao("DELETE", caminhoDoUsuario(id), undefined, true);
  dialogoExclusao.close();
  if (!resposta.ok) {
    await tratarFalha(resposta);
    return;
  }
  if (ehMinhaConta(id)) {
    limparSessao();
    irPara("/", "Sua conta de administrador foi excluída.");
    return;
  }
  usuarios = usuarios.filter((u) => String(u.id) !== String(id));
  if (selecionado && String(selecionado.id) === String(id)) selecionado = null;
  exibirDetalhe("ver");
  mostrarMensagem("Usuário excluído.", "sucesso");
}

botaoAtualizarLista.addEventListener("click", () => comBotaoOcupado(botaoAtualizarLista, () => carregarLista(true)));
document.getElementById("botao-editar-selecionado").addEventListener("click", () => editarUsuario(selecionado.id));
document.getElementById("botao-excluir-selecionado").addEventListener("click", () => pedirExclusao(selecionado.id));
document.getElementById("botao-cancelar-edicao").addEventListener("click", () => exibirDetalhe("ver"));
formEditarUsuario.addEventListener("submit", (e) => comBotaoOcupado(e.submitter ?? formEditarUsuario.querySelector("button"), () => salvarEdicao(e)));
document.getElementById("botao-cancelar-exclusao-usuario").addEventListener("click", () => dialogoExclusao.close());
botaoConfirmarExclusao.addEventListener("click", () => comBotaoOcupado(botaoConfirmarExclusao, confirmarExclusao));

if (paginaLiberada) carregarLista(false);
