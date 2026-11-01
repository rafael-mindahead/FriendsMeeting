# DESIGN.md — FriendsMeeting

## Produto e intenção
FriendsMeeting é um chat privado entre amigos (FastAPI, WebSocket e PostgreSQL). A pessoa precisa **encontrar uma conversa, enviar uma mensagem e continuar após reconectar** com segurança e sem distrações. O ESP32 é uma integração futura, não uma promessa da interface atual.

| Tela | Intenção | Variação | Movimento | Densidade |
|---|---|---|---|---|
| Landing | explicar o chat | média | baixa | baixa |
| Cadastro / login | entrar | baixa | baixa | média |
| Conversas | operar | baixa | baixa | média |
| Amigos / convites | operar | baixa | baixa | média |
| Perfil / preferências | operar | baixa | baixa | média |

## Identidade
- **Preservar:** grafite levemente esverdeado, verde-menta, símbolo de conversa; temas escuro e claro são igualmente importantes.
- **Tipografia:** sistema (SF Pro / Segoe UI), corpo em 15–17px, texto de apoio 13px quando AA; escala dos títulos sem letter-spacing inferior a -0.04em.
- **Espaçamento:** 4/8/12/16/24/32/48/64px.
- **Uma intenção por tela:** no chat a mensagem e o compositor dominam, no login o formulário domina.
- **Ícones:** SVG de traço consistente; não usar emojis como controles.
- **Foco:** sempre visível e não pode sumir quando WebSocket, presença ou lista mudarem.
- **Movimento:** até 200ms em estado; nada de animação cosmética. Respeitar reduced-motion.
- **Imagem:** preferir captura verdadeira do aplicativo; a ilustração HTML atual será marcada como *prévia demonstrativa* até haver screenshot real.

```design-tokens
fonts: SF Pro / Segoe UI (sistema), ui-monospace
colors: #091311, #10201b, #f7faf7, #f2f7f3, #73e4b2, #20875c
radii: 0, 10px, 14px, 20px
```

## Regras de UX
1. Mensagens novas não podem apagar rascunhos, reposicionar a janela do usuário que está lendo o histórico nem tirar foco de inputs.
2. Ao abrir conversa, exibir as 40 últimas mensagens e oferecer carregamento progressivo do histórico.
3. Convites devem identificar remetente por nome e avatar, não só UUID.
4. Usar microcopy concreta. Nenhum depoimento fictício atribuído a uma pessoa real.
5. Testar no mínimo 390×844, 768×1024 e 1440×900, com teclado e contraste AA.
6. Não fazer persistência de tokens JS no localStorage. A solução atual exige novo login após reload; evolução requer sessões HttpOnly e CSRF (mudança futura).
7. Sem alteração visual apenas para evitar 'cara de IA' se isso piorar clareza ou acessibilidade.

## Registro de decisões
### 2026-11-01 — Humanização orientada à tarefa
- Contexto: auditoria de `ui-humanizer` de Gabriel Greco e revisão da `develop`.
- Decisão: simplificar copy e ornamentação da landing, preservar a arquitetura familiar do chat, corrigir interações antes do polimento.
- Por quê: o que diferencia o FriendsMeeting é o fluxo real de comunicação, não um hero com gradiente ou cartões decorativos.
- Referência: https://github.com/gabrielgreco1/skills/tree/main/ui-humanizer
