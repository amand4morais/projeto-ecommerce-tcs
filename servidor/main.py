from api import criar_api
from controle_api import PORTA_PAINEL, ControleAPI
from log_requisicoes import LogRequisicoes
from painel import criar_painel


def main():
    log = LogRequisicoes()
    controle = ControleAPI(lambda: criar_api(log))
    painel = criar_painel(controle, log)
    print(f"Painel do servidor: http://127.0.0.1:{PORTA_PAINEL}")
    painel.run(host="127.0.0.1", port=PORTA_PAINEL, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
