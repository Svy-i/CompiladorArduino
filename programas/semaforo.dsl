# Semáforo onde o mesmo botão avança imediatamente para o próximo estado em qualquer fase.

BOTAO BOTAO_PEDESTRE = 2
INICIAL VERDE

ESTADO VERDE: tempo 10s, se BOTAO_PEDESTRE -> AMARELO -> AMARELO
ESTADO AMARELO: tempo 10s, se BOTAO_PEDESTRE -> VERMELHO -> VERMELHO
ESTADO VERMELHO: tempo 10s, se BOTAO_PEDESTRE -> VERDE -> VERDE