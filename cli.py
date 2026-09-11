from main import responder

historico = [
    {
        "role": "system",
        "content": (
            "Você é um assistente da prefeitura de Timon. "
            "Responda apenas sobre serviços municipais, clima e população. "
            "Use sempre as tools disponíveis para buscar informações. "
            "Nunca invente dados."
        )
    }
]

print("Agente iniciado. Digite 'sair' para encerrar.\n")

while True:
    entrada = input("Você: ")
    if entrada.lower() == "sair":
        break

    resposta = responder(entrada, historico)
    print(f"Agente: {resposta}\n")
