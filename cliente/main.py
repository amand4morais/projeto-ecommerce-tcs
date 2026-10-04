from app import criar_cliente

PORTA_CLIENTE = 5001


def main():
    print(f"Cliente: http://127.0.0.1:{PORTA_CLIENTE}")
    criar_cliente().run(host="127.0.0.1", port=PORTA_CLIENTE, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
