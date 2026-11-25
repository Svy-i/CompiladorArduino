import re
from dataclasses import dataclass


@dataclass
class Token:
    tipo: str
    valor: str
    linha: int
    coluna: int


TOKEN_RE = re.compile(
    r"""
    (?P<ESPACO>[ \t\r]+)
  | (?P<NEWLINE>\n)
  | (?P<COMENTARIO>\#[^\n]*)
  | (?P<SETA>->)
  | (?P<IGUAL>==)
  | (?P<ATRIB>=(?!=))
  | (?P<LBRACE>\{)
  | (?P<RBRACE>\})
  | (?P<LPAREN>\()
  | (?P<RPAREN>\))
  | (?P<DOIS_PONTOS>:)
  | (?P<VIRGULA>,)
  | (?P<PONTO_VIRGULA>;)
  | (?P<NUMERO>\d+)
  | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)


class ErroLexico(Exception):
    pass


def analisar(codigo: str) -> list[Token]:
    tokens = []
    posicao = 0
    linha = 1
    coluna = 1

    while posicao < len(codigo):
        match = TOKEN_RE.match(codigo, posicao)
        if not match:
            trecho = codigo[posicao:posicao + 12]
            raise ErroLexico(
                f"Caractere inesperado na linha {linha}, coluna {coluna}: {trecho!r}"
            )

        tipo = match.lastgroup
        valor = match.group()

        if tipo == "NEWLINE":
            linha += 1
            coluna = 1
        else:
            if tipo not in ("ESPACO", "COMENTARIO"):
                tokens.append(Token(tipo, valor, linha, coluna))
            coluna += len(valor)

        posicao = match.end()

    tokens.append(Token("EOF", "", linha, coluna))
    return tokens