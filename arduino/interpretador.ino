#include <Arduino.h>

const uint8_t PINO_VERMELHO = 9;
const uint8_t PINO_AMARELO  = 10;
const uint8_t PINO_VERDE    = 11;

const uint8_t MAX_ESTADOS = 32;
const uint8_t MAX_BOTOES  = 16;
const uint8_t MAX_REGRAS  = 64;

const uint8_t MASCARA_VERMELHO = 0x01;
const uint8_t MASCARA_AMARELO  = 0x02;
const uint8_t MASCARA_VERDE    = 0x04;

const unsigned long DEBOUNCE_MS = 50;

struct Estado {
  uint8_t mascaraLED;
  uint32_t duracaoMs;
  uint8_t proximoEstado;
  uint8_t inicioRegras;
  uint8_t qtdRegras;
};

struct Regra {
  uint8_t botaoIdx;
  uint8_t estadoDestino;
};

Estado tabela[MAX_ESTADOS];
uint8_t pinosBotoes[MAX_BOTOES];
Regra regras[MAX_REGRAS];

uint8_t quantidadeEstados = 0;
uint8_t quantidadeBotoes = 0;
uint8_t quantidadeRegras = 0;

uint8_t estadoAtual = 0;
unsigned long instanteEntrada = 0;
bool automatoCarregado = false;

// Estado de leitura e debounce dos botões (ativos em LOW com INPUT_PULLUP)
uint8_t leituraAnteriorBotao[MAX_BOTOES];
uint8_t estadoEstavelBotao[MAX_BOTOES];
unsigned long ultimoTempoDebounce[MAX_BOTOES];

bool lerBytes(uint8_t *destino, size_t quantidade) {
  size_t recebidos = Serial.readBytes(destino, quantidade);
  return recebidos == quantidade;
}

uint32_t lerUint32LittleEndian(const uint8_t *b) {
  return ((uint32_t)b[0]) |
         ((uint32_t)b[1] << 8) |
         ((uint32_t)b[2] << 16) |
         ((uint32_t)b[3] << 24);
}

void desligarLEDs() {
  digitalWrite(PINO_VERMELHO, LOW);
  digitalWrite(PINO_AMARELO, LOW);
  digitalWrite(PINO_VERDE, LOW);
}

void configurarBotoes() {
  for (uint8_t i = 0; i < quantidadeBotoes; i++) {
    pinMode(pinosBotoes[i], INPUT_PULLUP);
    leituraAnteriorBotao[i] = HIGH;
    estadoEstavelBotao[i] = HIGH;
    ultimoTempoDebounce[i] = 0;
  }
}

void aplicarEstado(uint8_t indice) {
  if (indice >= quantidadeEstados) {
    automatoCarregado = false;
    desligarLEDs();
    Serial.println(F("ERRO: indice de estado invalido."));
    return;
  }

  estadoAtual = indice;
  instanteEntrada = millis();

  uint8_t mascara = tabela[estadoAtual].mascaraLED;
  digitalWrite(PINO_VERMELHO, (mascara & MASCARA_VERMELHO) ? HIGH : LOW);
  digitalWrite(PINO_AMARELO,  (mascara & MASCARA_AMARELO)  ? HIGH : LOW);
  digitalWrite(PINO_VERDE,    (mascara & MASCARA_VERDE)    ? HIGH : LOW);

  Serial.print(F("Estado atual: "));
  Serial.println(estadoAtual);
}

// Detecta borda de descida (pressionamento) com debounce
bool botaoAcionado(uint8_t idx) {
  if (idx >= quantidadeBotoes) return false;

  uint8_t leitura = digitalRead(pinosBotoes[idx]);
  if (leitura != leituraAnteriorBotao[idx]) {
    ultimoTempoDebounce[idx] = millis();
  }
  leituraAnteriorBotao[idx] = leitura;

  if ((millis() - ultimoTempoDebounce[idx]) >= DEBOUNCE_MS) {
    if (leitura != estadoEstavelBotao[idx]) {
      estadoEstavelBotao[idx] = leitura;
      if (estadoEstavelBotao[idx] == LOW) {
        return true;
      }
    }
  }
  return false;
}

bool receberAutomato(uint8_t primeiroByte) {
  // O primeiro byte já deve ser 'F'. Recebe os outros 6 bytes do cabeçalho FSM2.
  if (primeiroByte != 'F') return false;

  uint8_t cabecalho[6];
  if (!lerBytes(cabecalho, sizeof(cabecalho))) {
    Serial.println(F("ERRO: cabecalho incompleto."));
    return false;
  }

  if (cabecalho[0] != 'S' || cabecalho[1] != 'M' || cabecalho[2] != '2') {
    Serial.println(F("ERRO: assinatura FSM2 invalida."));
    return false;
  }

  uint8_t inicial = cabecalho[3];
  uint8_t qtdEstados = cabecalho[4];
  uint8_t qtdBotoes = cabecalho[5];

  if (qtdEstados == 0 || qtdEstados > MAX_ESTADOS ||
      inicial >= qtdEstados || qtdBotoes > MAX_BOTOES) {
    Serial.println(F("ERRO: cabecalho fora dos limites."));
    return false;
  }

  uint8_t novosPinosBotoes[MAX_BOTOES];
  if (qtdBotoes > 0) {
    if (!lerBytes(novosPinosBotoes, qtdBotoes)) {
      Serial.println(F("ERRO: tabela de botoes incompleta."));
      return false;
    }
  }

  Estado novaTabela[MAX_ESTADOS];
  uint16_t totalRegras = 0;

  for (uint8_t i = 0; i < qtdEstados; i++) {
    uint8_t registro[8];
    if (!lerBytes(registro, sizeof(registro))) {
      Serial.println(F("ERRO: tabela de estados incompleta."));
      return false;
    }

    novaTabela[i].mascaraLED    = registro[0];
    novaTabela[i].duracaoMs     = lerUint32LittleEndian(&registro[1]);
    novaTabela[i].proximoEstado = registro[5];
    novaTabela[i].inicioRegras  = registro[6];
    novaTabela[i].qtdRegras     = registro[7];

    if (novaTabela[i].proximoEstado >= qtdEstados ||
        (novaTabela[i].mascaraLED & 0xF8) != 0 ||
        novaTabela[i].duracaoMs == 0) {
      Serial.println(F("ERRO: registro de estado invalido."));
      return false;
    }

    uint16_t fimRegra = (uint16_t)novaTabela[i].inicioRegras + novaTabela[i].qtdRegras;
    if (fimRegra > totalRegras) {
      totalRegras = fimRegra;
    }
  }

  if (totalRegras > MAX_REGRAS) {
    Serial.println(F("ERRO: quantidade de regras excede o limite."));
    return false;
  }

  Regra novasRegras[MAX_REGRAS];
  for (uint8_t i = 0; i < totalRegras; i++) {
    uint8_t reg[2];
    if (!lerBytes(reg, sizeof(reg))) {
      Serial.println(F("ERRO: tabela de regras incompleta."));
      return false;
    }

    novasRegras[i].botaoIdx = reg[0];
    novasRegras[i].estadoDestino = reg[1];

    if (novasRegras[i].botaoIdx >= qtdBotoes ||
        novasRegras[i].estadoDestino >= qtdEstados) {
      Serial.println(F("ERRO: regra condicional invalida."));
      return false;
    }
  }

  quantidadeBotoes = qtdBotoes;
  for (uint8_t i = 0; i < quantidadeBotoes; i++) {
    pinosBotoes[i] = novosPinosBotoes[i];
  }

  quantidadeEstados = qtdEstados;
  for (uint8_t i = 0; i < quantidadeEstados; i++) {
    tabela[i] = novaTabela[i];
  }

  quantidadeRegras = (uint8_t)totalRegras;
  for (uint8_t i = 0; i < quantidadeRegras; i++) {
    regras[i] = novasRegras[i];
  }

  configurarBotoes();
  automatoCarregado = true;
  desligarLEDs();
  aplicarEstado(inicial);
  Serial.println(F("OK: automato FSM2 carregado."));
  return true;
}

void setup() {
  pinMode(PINO_VERMELHO, OUTPUT);
  pinMode(PINO_AMARELO, OUTPUT);
  pinMode(PINO_VERDE, OUTPUT);
  desligarLEDs();

  Serial.begin(115200);
  Serial.setTimeout(3000);
  Serial.println(F("Interpretador FSM2 pronto. Aguardando automato..."));
}

void loop() {
  if (Serial.available() > 0) {
    int primeiro = Serial.read();
    if (primeiro == 'F') {
      receberAutomato((uint8_t)primeiro);
    }
  }

  if (!automatoCarregado) return;

  Estado &atual = tabela[estadoAtual];

  // 1. Verifica eventos de botões associados ao estado atual
  for (uint8_t i = 0; i < atual.qtdRegras; i++) {
    Regra &r = regras[atual.inicioRegras + i];
    if (botaoAcionado(r.botaoIdx)) {
      aplicarEstado(r.estadoDestino);
      return;
    }
  }

  // 2. Verifica transição por tempo esgotado
  if ((uint32_t)(millis() - instanteEntrada) >= atual.duracaoMs) {
    aplicarEstado(atual.proximoEstado);
  }
}