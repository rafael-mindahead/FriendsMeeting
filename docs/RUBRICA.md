# Mapa dos critérios de avaliação

Referência: enunciado do Projeto Final de Raciocínio Algorítmico. Este mapa relaciona evidências técnicas; não atribui nota, não comprova aprovação de opcionais e não substitui os registros individuais.

| Critério | Evidências verificáveis no código |
|---|---|
| Interação com o usuário (1,0) | [Interface web](../frontend/app.html), [fluxos JS](../frontend/js/app.js) |
| Processamento e regras de negócio (1,5) | [Amizades](../backend/app/routers/friends.py), [conversas](../backend/app/routers/conversations.py), [mensagens](../backend/app/routers/messages.py) |
| Controle de fluxo (1,0) | [Loop WebSocket e condições](../backend/app/routers/websocket_chat.py) |
| Organização e manipulação de dados (1,0) | [Dicionários de conexões e conjuntos de assinantes](../backend/app/realtime/manager.py), [modelos](../backend/app/models) |
| Modularização (1,0) | [Routers](../backend/app/routers), [serviços](../backend/app/services), [cliente de autenticação](../backend/app/clients/auth_service.py) |
| Confiabilidade (1,5) | [Testes](../backend/tests), tratamento de exceções e validação de entradas |
| Interface gráfica (opcional, 1,5) | [Frontend](../frontend), operações integradas às APIs |
| Persistência (opcional, 1,0) | [Modelos](../backend/app/models), [migrations](../backend/migrations), [Compose](../compose.yaml) |
| Visualização de informações (opcional, 1,0) | Histórico, datas de mensagens e estado de presença; aceitação do critério depende da avaliação da professora |
| Funcionalidade adicional (opcional, 1,5) | WebSocket e anexos são evidências técnicas; requer aprovação prévia da proposta e seus critérios |
| Integração externa (opcional, 1,5) | Cliente HTTP do authService independente; por ser serviço próprio, não presumir que atende ao critério de API externa |

Demonstração reproduzível: seguir [README](../README.md), testar dois usuários, mensagens, reconexão e histórico. Verificar os resultados reais em [Actions](https://github.com/rafael-mindahead/FriendsMeeting/actions). A avaliação individual considera as três sprints e a apresentação; os registros de cada integrante devem ser entregues separadamente.
