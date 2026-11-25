"""Analisador sintático: transforma tokens em uma AST para autômatos com botões."""


class ErroSintatico(Exception):
    pass


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def atual(self):
        return self.tokens[self.pos]

    def avancar(self):
        token = self.atual()
        if token.tipo != "EOF":
            self.pos += 1
        return token

    def aceitar(self, tipo):
        if self.atual().tipo == tipo:
            return self.avancar()
        return None

    def exigir(self, tipo, descricao=None):
        token = self.aceitar(tipo)
        if token is None:
            atual = self.atual()
            esperado = descricao or tipo
            raise ErroSintatico(
                f"Linha {atual.linha}, coluna {atual.coluna}: "
                f"esperado {esperado}, encontrado {atual.valor or atual.tipo!r}"
            )
        return token

    def palavra(self, valor):
        token = self.atual()
        if token.tipo == "IDENT" and token.valor.upper() == valor:
            return self.avancar()
        return None

    def exigir_palavra(self, valor):
        token = self.palavra(valor)
        if token is None:
            atual = self.atual()
            raise ErroSintatico(
                f"Linha {atual.linha}, coluna {atual.coluna}: "
                f"esperada a palavra {valor}"
            )
        return token

    def _ler_duracao_ms(self):
        numero = int(self.exigir("NUMERO", "duração numérica").valor)
        unidade = self.exigir("IDENT", "unidade s ou ms").valor.lower()
        if unidade not in ("s", "ms"):
            raise ErroSintatico(
                f"Unidade inválida {unidade!r}; utilize 's' ou 'ms'"
            )
        return numero * 1000 if unidade == "s" else numero

    def _inferir_led_por_nome(self, nome_estado):
        upper = nome_estado.upper()
        if upper in ("VERMELHO", "AMARELO", "VERDE"):
            return upper
        return "NENHUM"

    def analisar_completo(self):
        nome = "Automato"
        inicial = None
        botoes = []
        estados = []
        usa_bloco_automato = False

        if self.palavra("AUTOMATO"):
            usa_bloco_automato = True
            nome = self.exigir("IDENT", "nome do autômato").valor
            self.exigir("LBRACE", "'{'")

        while self.atual().tipo not in ("RBRACE", "EOF"):
            if self.palavra("INICIAL"):
                inicial = self.exigir("IDENT", "nome do estado inicial").valor
                self.aceitar("PONTO_VIRGULA")

            elif self.palavra("BOTAO"):
                nome_botao = self.exigir("IDENT", "nome do botão").valor
                self.exigir("ATRIB", "'='")
                pino = int(self.exigir("NUMERO", "número do pino do botão").valor)
                self.aceitar("PONTO_VIRGULA")
                botoes.append({"nome": nome_botao, "pino": pino})

            elif self.palavra("ESTADO"):
                estados.append(self.analisar_estado())

            else:
                t = self.atual()
                raise ErroSintatico(
                    f"Linha {t.linha}, coluna {t.coluna}: "
                    f"declaração inesperada {t.valor!r}"
                )

        if usa_bloco_automato:
            self.exigir("RBRACE", "'}'")

        self.exigir("EOF", "fim do arquivo")

        if inicial is None and estados:
            inicial = estados[0]["nome"]

        return {
            "nome": nome,
            "inicial": inicial,
            "botoes": botoes,
            "estados": estados,
        }

    def analisar_estado(self):
        nome_estado = self.exigir("IDENT", "nome do estado").valor

        # Formato compacto em linha:
        # ESTADO VERDE: tempo 10s, se BOTAO_PEDESTRE -> AMARELO -> AMARELO
        if self.aceitar("DOIS_PONTOS"):
            return self._analisar_estado_linha(nome_estado)

        # Formato em bloco:
        # ESTADO VERDE { LED_VERDE = ON; tempo 10s -> AMARELO; se BOTAO_PEDESTRE -> AMARELO; }
        self.exigir("LBRACE", "':' ou '{'")
        return self._analisar_estado_bloco(nome_estado)

    def _analisar_estado_linha(self, nome_estado):
        led = None
        duracao = None
        destino = None
        regras = []

        while self.atual().tipo != "EOF":
            # Encerra se começar uma nova declaração de topo
            if self.atual().tipo == "IDENT" and self.atual().valor.upper() in (
                "ESTADO",
                "BOTAO",
                "INICIAL",
            ):
                break

            if self.palavra("LED"):
                cor = self.exigir("IDENT", "cor do LED (VERMELHO, AMARELO, VERDE, NENHUM)").valor.upper()
                if cor not in ("VERMELHO", "AMARELO", "VERDE", "NENHUM"):
                    raise ErroSintatico(f"Cor de LED inválida: {cor!r}")
                led = cor

            elif self.palavra("TEMPO"):
                if duracao is not None:
                    raise ErroSintatico(f"Estado {nome_estado!r}: tempo definido mais de uma vez.")
                duracao = self._ler_duracao_ms()
                if self.aceitar("SETA"):
                    destino = self.exigir("IDENT", "estado de destino").valor

            elif self.palavra("SE"):
                botao = self.exigir("IDENT", "nome do botão").valor
                self.exigir("SETA", "'->'")
                destino_regra = self.exigir("IDENT", "estado de destino da regra").valor
                regras.append({"botao": botao, "destino": destino_regra})

            elif self.aceitar("SETA"):
                if destino is not None:
                    raise ErroSintatico(f"Estado {nome_estado!r}: transição padrão '->' duplicada.")
                destino = self.exigir("IDENT", "estado de destino").valor

            else:
                t = self.atual()
                raise ErroSintatico(
                    f"Linha {t.linha}, coluna {t.coluna}: "
                    f"token inesperado {t.valor!r} na regra do estado {nome_estado!r}"
                )

            if self.aceitar("PONTO_VIRGULA"):
                break
            if not self.aceitar("VIRGULA"):
                # Permite encadear '-> DESTINO' sem vírgula após 'se BOTAO -> OUTRO'
                if self.atual().tipo != "SETA":
                    break

        return {
            "nome": nome_estado,
            "led": led if led is not None else self._inferir_led_por_nome(nome_estado),
            "duracao_ms": duracao,
            "destino": destino,
            "regras": regras,
        }

    def _analisar_estado_bloco(self, nome_estado):
        led = None
        duracao = None
        destino = None
        regras = []

        while self.atual().tipo != "RBRACE":
            if self.atual().tipo == "EOF":
                self.exigir("RBRACE", "'}'")

            if self.palavra("LED_VERMELHO"):
                led = self._ler_atribuicao_led(led, "VERMELHO")
            elif self.palavra("LED_AMARELO"):
                led = self._ler_atribuicao_led(led, "AMARELO")
            elif self.palavra("LED_VERDE"):
                led = self._ler_atribuicao_led(led, "VERDE")
            elif self.palavra("APOS") or self.palavra("TEMPO"):
                if duracao is not None:
                    raise ErroSintatico("Use apenas uma definição de tempo/APOS por estado.")
                duracao = self._ler_duracao_ms()
                if self.aceitar("SETA"):
                    destino = self.exigir("IDENT", "estado de destino").valor
                self.aceitar("PONTO_VIRGULA")
            elif self.palavra("SE"):
                botao = self.exigir("IDENT", "nome do botão").valor
                self.exigir("SETA", "'->'")
                destino_regra = self.exigir("IDENT", "estado de destino da regra").valor
                self.aceitar("PONTO_VIRGULA")
                regras.append({"botao": botao, "destino": destino_regra})
            elif self.aceitar("SETA"):
                if destino is not None:
                    raise ErroSintatico("Use apenas uma transição padrão '->' por estado.")
                destino = self.exigir("IDENT", "estado de destino").valor
                self.aceitar("PONTO_VIRGULA")
            else:
                t = self.atual()
                raise ErroSintatico(
                    f"Linha {t.linha}, coluna {t.coluna}: instrução inesperada {t.valor!r}"
                )

        self.exigir("RBRACE", "'}'")
        return {
            "nome": nome_estado,
            "led": led if led is not None else self._inferir_led_por_nome(nome_estado),
            "duracao_ms": duracao,
            "destino": destino,
            "regras": regras,
        }

    def _ler_atribuicao_led(self, led_atual, cor):
        self.exigir("ATRIB", "'='")
        valor = self.exigir("IDENT", "ON ou OFF").valor.upper()
        if valor not in ("ON", "OFF"):
            raise ErroSintatico("A ação do LED deve ser ON ou OFF.")
        if led_atual is not None:
            raise ErroSintatico("Use no máximo uma ação de LED por estado.")
        self.exigir("PONTO_VIRGULA", "';'")
        return cor if valor == "ON" else "NENHUM"


def analisar(tokens):
    """Ponto de entrada utilizado por main.py."""
    parser = Parser(tokens)
    return parser.analisar_completo()