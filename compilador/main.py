"""Compila um arquivo .dsl para automato.bin e, opcionalmente, envia ao Arduino."""

import argparse
import sys
import time
from pathlib import Path

from lexer import analisar as analisar_lexico, ErroLexico
from parser import analisar as analisar_sintatico, ErroSintatico
from semantico import analisar as analisar_semantico, ErroSemantico
from gerador import gerar


def enviar_serial(dados: bytes, porta: str, baudrate: int):
    try:
        import serial
    except ImportError:
        raise RuntimeError(
            "Para enviar pela serial, instale pyserial: python -m pip install pyserial"
        )

    with serial.Serial(porta, baudrate, timeout=2) as conexao:
        # Muitas placas Arduino reiniciam quando a porta serial é aberta.
        time.sleep(2)
        conexao.reset_input_buffer()
        conexao.write(dados)
        conexao.flush()
        print(f"Arquivo enviado para {porta} ({len(dados)} bytes).")


def main():
    raiz = Path(__file__).resolve().parent.parent
    parser_args = argparse.ArgumentParser(
        description="Compilador da DSL de autômatos para Arduino."
    )
    parser_args.add_argument(
        "arquivo", nargs="?", default=str(raiz / "programas" / "semaforo.dsl"),
        help="arquivo de entrada .dsl"
    )
    parser_args.add_argument(
        "-o", "--saida", default=str(raiz / "saida" / "automato.bin"),
        help="arquivo binário de saída"
    )
    parser_args.add_argument("--port", help="porta serial, por exemplo COM3")
    parser_args.add_argument("--baud", type=int, default=115200)
    args = parser_args.parse_args()

    caminho_entrada = Path(args.arquivo)
    caminho_saida = Path(args.saida)

    try:
        codigo = caminho_entrada.read_text(encoding="utf-8")
        tokens = analisar_lexico(codigo)
        ast = analisar_sintatico(tokens)
        analisar_semantico(ast)
        bytecode = gerar(ast)

        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        caminho_saida.write_bytes(bytecode)

        total_regras = sum(len(e.get("regras", [])) for e in ast["estados"])
        print(f"Compilação concluída: {caminho_saida}")
        print(f"Autômato: {ast['nome']}")
        print(f"Estados: {len(ast['estados'])} | Botões: {len(ast.get('botoes', []))} | Regras: {total_regras}")
        print(f"Tamanho: {len(bytecode)} bytes")

        if args.port:
            enviar_serial(bytecode, args.port, args.baud)

    except (OSError, ErroLexico, ErroSintatico, ErroSemantico, RuntimeError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()