import struct

MASCARAS_LED = {
    "NENHUM": 0,
    "VERMELHO": 1,
    "AMARELO": 2,
    "VERDE": 4,
}


def gerar(ast):
    estados = ast["estados"]
    botoes = ast.get("botoes", [])

    indices_estados = {estado["nome"]: i for i, estado in enumerate(estados)}
    indices_botoes = {botao["nome"]: i for i, botao in enumerate(botoes)}
    inicial = indices_estados[ast["inicial"]]

    dados = bytearray(b"FSM2")
    dados.append(inicial)
    dados.append(len(estados))
    dados.append(len(botoes))

    # 1. Tabela de pinos dos botões
    for botao in botoes:
        dados.append(botao["pino"])

    # 2. Tabela de estados + acumulação das regras condicionais
    regras_serializadas = bytearray()
    for estado in estados:
        mascara = MASCARAS_LED[estado["led"]]
        duracao = estado["duracao_ms"]
        destino = indices_estados[estado["destino"]]

        regras_estado = estado.get("regras", [])
        inicio_regras = len(regras_serializadas) // 2
        qtd_regras = len(regras_estado)

        dados.extend(
            struct.pack(
                "<BIBBB",
                mascara,
                duracao,
                destino,
                inicio_regras,
                qtd_regras,
            )
        )

        for regra in regras_estado:
            idx_botao = indices_botoes[regra["botao"]]
            idx_destino = indices_estados[regra["destino"]]
            regras_serializadas.extend(struct.pack("<BB", idx_botao, idx_destino))

    dados.extend(regras_serializadas)

    return bytes(dados)