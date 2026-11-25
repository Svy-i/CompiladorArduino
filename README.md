# CompiladorArduino

Projeto didático: compilador de uma DSL simples para um interpretador de autômatos no Arduino Uno.

## Requisitos
- Python 3.10+
- Arduino IDE
- Arduino Uno (ou placa compatível)
- Opcional: `python -m pip install pyserial` para envio direto pela serial

## Compilar no computador
Na raiz do projeto:

```bash
python compilador/main.py
```

Isso lê `programas/semaforo.dsl` e gera `saida/automato.bin`.

Para compilar outro arquivo:

```bash
python compilador/main.py programas/meu_programa.dsl
```

## Enviar para o Arduino
1. Abra `arduino/interpretador.ino` na Arduino IDE.
2. Selecione a placa e a porta corretas e faça upload do sketch.
3. Feche o Monitor Serial da Arduino IDE (a porta não pode estar ocupada).
4. Instale pyserial: `python -m pip install pyserial`.
5. Envie (troque COM3 pela porta correta):

```bash
python compilador/main.py --port COM3
```

Linux pode usar, por exemplo, `/dev/ttyACM0`.

## Ligações
- LED vermelho: pino 9 -> resistor de 220 a 330 ohms -> ânodo do LED; cátodo ao GND.
- LED amarelo: pino 10 -> resistor de 220 a 330 ohms -> ânodo do LED; cátodo ao GND.
- LED verde: pino 11 -> resistor de 220 a 330 ohms -> ânodo do LED; cátodo ao GND.

Use um resistor para cada LED. Não ligue LEDs diretamente aos pinos sem resistores.

## Sintaxe implementada
```text
AUTOMATO Nome {
    INICIAL EstadoInicial;
    ESTADO NomeEstado {
        LED_VERMELHO = ON;
        APOS 5s -> ProximoEstado;
    }
}
```

Cada estado deve conter exatamente uma transição `APOS`. Unidades aceitas: `s` e `ms`.
Cada estado pode acender no máximo um dos três LEDs (ou nenhum com `= OFF`).
O interpretador suporta até 32 estados.

## Limitações desta primeira versão
- Transições somente por temporização; ainda não há leitura de botões/sensores.
- O compilador é didático e não implementa recuperação de erros sofisticada.
- O binário é um formato próprio simples (`FSM1`), não um formato padrão.
- O Arduino recebe o arquivo pela serial a 115200 baud.
