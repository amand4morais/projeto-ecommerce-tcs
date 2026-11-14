const listaProdutos = document.getElementById("lista-produtos");
const dicaProdutos = document.getElementById("dica-produtos");
const botaoAtualizarProdutos = document.getElementById("botao-atualizar-produtos");
const botaoNovoProduto = document.getElementById("botao-novo-produto");
const idProduto = document.getElementById("id-produto");
const produtoVazio = document.getElementById("produto-vazio");
const produtoVer = document.getElementById("produto-ver");
const dadosProduto = document.getElementById("dados-produto");
const formProduto = document.getElementById("form-produto");
const dialogoExclusao = document.getElementById("dialogo-exclusao-produto");
const botaoConfirmarExclusao = document.getElementById("botao-confirmar-exclusao-produto");
const PADRAO_NUMERO = /^-?\d+(\.\d+)?$/;

const ehAdmin = obterSessao()?.usuario?.admin === true;
let produtos = [];
let selecionado = null;
let modoFormulario = null;

const caminhoDoProduto = (id) => `/products/${encodeURIComponent(String(id))}`;
const mesmoId = (a, b) => String(a) === String(b);

function converterQuantidade(texto) {
  const valor = texto.trim();
  return PADRAO_NUMERO.test(valor) ? Number(valor) : texto;
}

function textoEstoque(quantidade) {
  if (quantidade === 0) return "Esgotado";
  return quantidade === 1 ? "unidade" : "unidades";
}

function bilheteDoProduto(produto) {
  const item = criarElemento("li", "bilhete");
  if (selecionado && mesmoId(selecionado.id, produto.id)) item.classList.add("bilhete-selecionado");

  const principal = criarElemento("div", "bilhete-principal");
  principal.append(
    criarElemento("p", "bilhete-numero", `Nº ${produto.id}`),
    criarElemento("p", "bilhete-nome", produto.nome ?? "—"),
    criarElemento("p", "bilhete-descricao", produto.descricao || "Sem descrição."),
  );

  const canhoto = criarElemento("div", "bilhete-canhoto");
  const quantidade = criarElemento("p", produto.quantidade === 0 ? "bilhete-quantidade esgotado" : "bilhete-quantidade", produto.quantidade ?? "—");
  const botao = criarElemento("button", "botao botao-pequeno botao-secundario", "Consultar");
  botao.type = "button";
  botao.setAttribute("aria-label", `Consultar ${produto.nome ?? `produto ${produto.id}`}`);
  botao.addEventListener("click", () => comBotaoOcupado(botao, () => consultarProduto(produto.id)));
  canhoto.append(quantidade, criarElemento("p", "bilhete-unidade", textoEstoque(produto.quantidade)), botao);

  item.append(principal, canhoto);
  return item;
}

function exibirLista() {
  listaProdutos.replaceChildren(...produtos.map(bilheteDoProduto));
  dicaProdutos.hidden = produtos.length > 0;
  if (produtos.length === 0) {
    dicaProdutos.textContent = ehAdmin ? "Nenhum produto cadastrado. Use \"Novo produto\" para começar." : "Nenhum produto cadastrado neste servidor.";
  }
}

function exibirPainel(modo) {
  modoFormulario = modo === "novo" || modo === "editar" ? modo : null;
  produtoVazio.hidden = Boolean(selecionado) || modoFormulario === "novo";
  produtoVer.hidden = !selecionado || modo !== "ver";
  formProduto.hidden = !modoFormulario;
  idProduto.textContent = selecionado && modo !== "novo" ? `Nº ${selecionado.id}` : "";

  if (selecionado && modo === "ver") {
    document.getElementById("estoque-valor").textContent = selecionado.quantidade ?? "—";
    dadosProduto.replaceChildren();
    for (const [rotulo, valor] of [["Id", selecionado.id], ["Nome", selecionado.nome], ["Descrição", selecionado.descricao || "Sem descrição."], ["Quantidade", selecionado.quantidade]]) {
      dadosProduto.append(criarElemento("dt", null, rotulo), criarElemento("dd", null, valor ?? "—"));
    }
  }
  if (modoFormulario) {
    const editando = modoFormulario === "editar";
    document.getElementById("titulo-form-produto").textContent = editando ? "Editar produto" : "Novo produto";
    document.getElementById("botao-salvar-produto").textContent = editando ? "Salvar alterações" : "Cadastrar";
    formProduto.elements.nome.value = editando ? selecionado.nome ?? "" : "";
    formProduto.elements.descricao.value = editando ? selecionado.descricao ?? "" : "";
    formProduto.elements.quantidade.value = editando ? String(selecionado.quantidade ?? "") : "";
    formProduto.elements.nome.focus();
  }
  exibirLista();
}

async function carregarProdutos(avisar) {
  const resposta = await enviarRequisicao("GET", "/products", undefined, true);
  if (resposta.status === 401) return;
  if (!resposta.ok) {
    dicaProdutos.textContent = "Não foi possível carregar os produtos.";
    mostrarMensagem(resposta.mensagem, "erro");
    return;
  }
  if (!Array.isArray(resposta.corpo)) {
    dicaProdutos.textContent = "O servidor respondeu à listagem em um formato inesperado.";
    mostrarMensagem(dicaProdutos.textContent, "erro");
    return;
  }
  produtos = resposta.corpo;
  if (selecionado && !produtos.some((p) => mesmoId(p.id, selecionado.id))) {
    selecionado = null;
    exibirPainel("ver");
  }
  exibirLista();
  if (avisar) mostrarMensagem("Lista de produtos atualizada.", "sucesso");
}

async function tratarFalha(resposta) {
  if (resposta.status === 401) return;
  mostrarMensagem(resposta.mensagem, "erro");
  if (resposta.status === 404) await carregarProdutos(false);
}

function atualizarProdutoNaLista(produto) {
  const existe = produtos.some((p) => mesmoId(p.id, produto.id));
  produtos = existe ? produtos.map((p) => (mesmoId(p.id, produto.id) ? { ...p, ...produto } : p)) : [...produtos, produto];
}

async function consultarProduto(id) {
  const resposta = await enviarRequisicao("GET", caminhoDoProduto(id), undefined, true);
  if (!resposta.ok) {
    await tratarFalha(resposta);
    return;
  }
  selecionado = resposta.corpo && typeof resposta.corpo === "object" ? resposta.corpo : { id };
  atualizarProdutoNaLista(selecionado);
  exibirPainel("ver");
  mostrarMensagem(`Estoque de ${selecionado.nome ?? `produto ${id}`} consultado no servidor: ${selecionado.quantidade}.`, "sucesso");
}

async function cadastrarProduto(campos) {
  const corpo = { nome: campos.nome, descricao: campos.descricao, quantidade: converterQuantidade(campos.quantidade) };
  const resposta = await enviarRequisicao("POST", "/products", corpo, true);
  if (!resposta.ok) {
    await tratarFalha(resposta);
    return;
  }
  selecionado = resposta.corpo && typeof resposta.corpo === "object" ? resposta.corpo : null;
  if (selecionado) atualizarProdutoNaLista(selecionado);
  exibirPainel("ver");
  mostrarMensagem("Produto cadastrado.", "sucesso");
}

async function salvarEdicao(campos) {
  const corpo = {};
  if (campos.nome !== (selecionado.nome ?? "")) corpo.nome = campos.nome;
  if (campos.descricao !== (selecionado.descricao ?? "")) corpo.descricao = campos.descricao;
  if (campos.quantidade !== String(selecionado.quantidade ?? "")) corpo.quantidade = converterQuantidade(campos.quantidade);
  if (Object.keys(corpo).length === 0) {
    mostrarMensagem("Nenhuma alteração para enviar.");
    return;
  }
  const resposta = await enviarRequisicao("PATCH", caminhoDoProduto(selecionado.id), corpo, true);
  if (!resposta.ok) {
    await tratarFalha(resposta);
    return;
  }
  selecionado = { ...selecionado, ...(resposta.corpo && typeof resposta.corpo === "object" ? resposta.corpo : corpo) };
  atualizarProdutoNaLista(selecionado);
  exibirPainel("ver");
  mostrarMensagem("Produto atualizado.", "sucesso");
}

async function enviarFormulario(evento) {
  evento.preventDefault();
  const campos = lerCampos(formProduto, ["nome", "descricao", "quantidade"]);
  if (modoFormulario === "novo") await cadastrarProduto(campos);
  else await salvarEdicao(campos);
}

function pedirExclusao() {
  document.getElementById("texto-exclusao-produto").textContent =
    `O produto ${selecionado.nome ?? `Nº ${selecionado.id}`} será removido do estoque deste servidor. Esta ação não pode ser desfeita.`;
  dialogoExclusao.showModal();
}

async function confirmarExclusao() {
  const id = selecionado.id;
  const resposta = await enviarRequisicao("DELETE", caminhoDoProduto(id), undefined, true);
  dialogoExclusao.close();
  if (!resposta.ok) {
    await tratarFalha(resposta);
    return;
  }
  produtos = produtos.filter((p) => !mesmoId(p.id, id));
  selecionado = null;
  exibirPainel("ver");
  mostrarMensagem("Produto excluído.", "sucesso");
}

botaoNovoProduto.hidden = !ehAdmin;
document.getElementById("acoes-adm-produto").hidden = !ehAdmin;
botaoAtualizarProdutos.addEventListener("click", () => comBotaoOcupado(botaoAtualizarProdutos, () => carregarProdutos(true)));
botaoNovoProduto.addEventListener("click", () => { mostrarMensagem(""); exibirPainel("novo"); });
document.getElementById("botao-editar-produto").addEventListener("click", () => { mostrarMensagem(""); exibirPainel("editar"); });
document.getElementById("botao-excluir-produto").addEventListener("click", pedirExclusao);
document.getElementById("botao-cancelar-produto").addEventListener("click", () => exibirPainel("ver"));
formProduto.addEventListener("submit", (e) => comBotaoOcupado(e.submitter ?? formProduto.querySelector("button"), () => enviarFormulario(e)));
document.getElementById("botao-cancelar-exclusao-produto").addEventListener("click", () => dialogoExclusao.close());
botaoConfirmarExclusao.addEventListener("click", () => comBotaoOcupado(botaoConfirmarExclusao, confirmarExclusao));

if (paginaLiberada) carregarProdutos(false);
