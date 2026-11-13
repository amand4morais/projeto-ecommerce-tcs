const seloApi = document.getElementById("selo-api");
const seloTexto = document.getElementById("selo-texto");

function criarElemento(tag, classe, texto) {
  const elemento = document.createElement(tag);
  if (classe) elemento.className = classe;
  if (texto !== undefined && texto !== null) elemento.textContent = texto;
  return elemento;
}

function classeDoStatus(status) {
  if (status >= 500) return "status status-falha";
  if (status >= 400) return "status status-erro";
  return "status status-ok";
}

async function buscarJSON(caminho) {
  const resposta = await fetch(caminho);
  return resposta.json();
}

async function atualizarEstadoApi() {
  try {
    const estado = await buscarJSON("/estado");
    seloApi.dataset.rodando = String(estado.rodando);
    seloTexto.textContent = estado.rodando ? `API na porta ${estado.porta}` : "API parada";
    document.dispatchEvent(new CustomEvent("estado-api", { detail: estado }));
  } catch {
    seloApi.dataset.rodando = "false";
    seloTexto.textContent = "Painel sem resposta";
  }
}

atualizarEstadoApi();
setInterval(atualizarEstadoApi, 2000);
