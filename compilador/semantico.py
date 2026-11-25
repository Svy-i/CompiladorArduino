"""Verificações semânticas da DSL."""


class ErroSemantico(Exception):
    pass


PINOS_LEDS_RESERVADOS = {9, 10, 11}
MAX_ESTADOS = 32
MAX_BOTOES = 16
MAX_REGRAS = 64


def analisar(ast):
    estados = ast["estados"]
    botoes = ast.get("botoes", [])

    if not estados:
        raise ErroSemantico("O autômato precisa ter pelo menos um estado.")

    nomes_estados = [estado["nome"] for estado in estados]
    if len(nomes_estados) != len(set(nomes_estados)):
        raise ErroSemantico("Existem estados com nomes repetidos.")

    if len(estados) > MAX_ESTADOS:
        raise ErroSemantico(f"Esta versão suporta no máximo {MAX_ESTADOS} estados.")

    if ast["inicial"] not in nomes_estados:
        raise ErroSemantico(
            f"O estado inicial {ast['inicial']!r} não foi declarado."
        )

    if len(botoes) > MAX_BOTOES:
        raise ErroSemantico(f"Esta versão suporta no máximo {MAX_BOTOES} botões.")

    nomes_botoes = [b["nome"] for b in botoes]
    if len(nomes_botoes) != len(set(nomes_botoes)):
        raise ErroSemantico("Existem botões com nomes repetidos.")

    pinos_usados = set()
    for b in botoes:
        pino = b["pino"]
        if pino < 2 or pino > 53:
            raise ErroSemantico(
                f"Pino inválido ({pino}) para o botão {b['nome']!r}."
            )
        if pino in PINOS_LEDS_RESERVADOS:
            raise ErroSemantico(
                f"O pino {pino} do botão {b['nome']!r} conflita com os pinos dos LEDs (9, 10, 11)."
            )
        if pino in pinos_usados:
            raise ErroSemantico(
                f"O pino {pino} está atribuído a mais de um botão."
            )
        pinos_usados.add(pino)

    estados_conhecidos = set(nomes_estados)
    botoes_conhecidos = set(nomes_botoes)
    total_regras = 0

    for idx, estado in enumerate(estados):
        if estado["duracao_ms"] is None:
            raise ErroSemantico(
                f"O estado {estado['nome']!r} precisa definir um tempo (ex.: tempo 10s)."
            )
        if estado["duracao_ms"] <= 0:
            raise ErroSemantico(
                f"A duração do estado {estado['nome']!r} deve ser maior que zero."
            )
        if estado["duracao_ms"] > 4_294_967_295:
            raise ErroSemantico("Duração excede o limite de 32 bits.")

        # Se nenhum destino por tempo foi explicitado, permanece no próprio estado
        if estado["destino"] is None:
            estado["destino"] = estado["nome"]

        if estado["destino"] not in estados_conhecidos:
            raise ErroSemantico(
                f"O estado {estado['nome']!r} aponta para "
                f"{estado['destino']!r}, que não existe."
            )

        proximo_da_sequencia = estados[(idx + 1) % len(estados)]["nome"]
        regras = estado.get("regras", [])
        total_regras += len(regras)

        for regra in regras:
            if regra["botao"] not in botoes_conhecidos:
                raise ErroSemantico(
                    f"No estado {estado['nome']!r}, o botão {regra['botao']!r} "
                    f"não foi declarado com 'BOTAO {regra['botao']} = <PINO>;'."
                )

            if regra["destino"].upper() == "PROXIMO":
                regra["destino"] = (
                    estado["destino"]
                    if estado["destino"] != estado["nome"]
                    else proximo_da_sequencia
                )

            if regra["destino"] not in estados_conhecidos:
                raise ErroSemantico(
                    f"No estado {estado['nome']!r}, a regra para {regra['botao']!r} "
                    f"aponta para {regra['destino']!r}, que não existe."
                )

    if total_regras > MAX_REGRAS:
        raise ErroSemantico(f"Esta versão suporta no máximo {MAX_REGRAS} regras de transição.")

    return True