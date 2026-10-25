# FriendsMeeting — arquitetura e contratos (backend HTTP)

## Escopo implementado

- **FastAPI FriendsMeeting**: identidade local (UUID), convites de amizade, conversas e mensagens.
- **authService**: contas, credenciais, tokens e sessões; FastAPI FriendsMeeting consulta `/auth/me` usando o bearer recebido.
- **PostgreSQL FriendsMeeting**: `users`, `friend_requests`, `conversations`, `messages`.
- **PostgreSQL authService + Redis**: responsabilidades exclusivas do serviço de autenticação.
- **WebSocket/ESP32**: **planejados**, ainda não integrados; o transporte atual é HTTP.

## Modelo de dados

```text
users(id: uuid, username, email, auth_user_id?, friend_code, created_at)
  |
  +-- friend_requests(id, sender_id, receiver_id, status, created_at, responded_at)
  |     status: pending | accepted | rejected
  |     indice unico por par nao ordenado; CHECK contra auto-convite
  |
  +-- conversations(id, user_a_id, user_b_id, created_at)
        indice unico por par nao ordenado; CHECK para participantes distintos
        |
        +-- messages(id, conversation_id, sender_id, body, created_at)
              CHECK: char_length(btrim(body)) entre 1 e 2000
              indice por conversation_id + created_at + id
```

Uma amizade aceita é representada por `friend_requests.status = 'accepted'`, sem tabela adicional. Criar uma conversa requer amizade aceita; o endpoint retorna **201** para uma conversa nova e **200** se o par já tem conversa.

## Endpoints e autorização

| Método | Rota | Contrato / comportamento |
|---|---|---|
| POST | `/api/v1/auth/register` | Cadastro delegado ao authService |
| POST | `/api/v1/auth/login` | Login delegado ao authService |
| GET | `/api/v1/users/me` | Perfil local UUID associado ao JWT |
| POST | `/api/v1/friends/requests` | Enviar convite por `friend_code` |
| GET | `/api/v1/friends/requests` | Pendentes recebidos |
| PATCH | `/api/v1/friends/requests/{id}` | `{"action":"accept"|"reject"}` pelo destinatário |
| GET | `/api/v1/friends` | Amigos aceitos |
| POST | `/api/v1/conversations` | `{"friend_id":"UUID"}`, somente amigos |
| GET | `/api/v1/conversations` | Conversas de que o usuário participa |
| GET | `/api/v1/conversations/{id}` | Detalhes, somente participantes |
| POST | `/api/v1/conversations/{id}/messages` | `{"body":"mensagem"}` (1–2000 caracteres, não em branco) |
| GET | `/api/v1/conversations/{id}/messages` | Histórico `limit=1..100`, `offset>=0`, mais recente primeiro |

Todas as rotas acima, exceto `/auth/*`, exigem Bearer válido. As chamadas por usuário não recebem `sender_id` arbitrário do cliente: a API deriva o remetente de `get_current_user`. Consultas de terceiros a conversas retornam **404** sem revelar se a conversa existe.

## Pontos de atenção

1. **Paginação `offset`**: suficiente para MVP; futuramente preferir cursor (`created_at`, `id`) para evitar deslocamentos enquanto novas mensagens chegam.
2. **Autorização do banco**: a API verifica participação, mas as FKs de `messages` sozinhas não restringem remetentes aos dois participantes. Evitar escrita direta no banco fora dessa API; considerar reforço no banco conforme necessidade.
3. **Sem tempo real**: não há conexão WebSocket, entrega push, confirmações de leitura ou fila offline implantadas.
4. **ESP32 offline**: precisará autenticação local adequada, política de retenção e sincronização ao retornar a API, sem prometer acesso ao PostgreSQL quando ela estiver desligada.
5. **CI**: executa migracoes reais em banco temporário, testes com mocks e testes PostgreSQL. O banco do Compose principal não participa da suíte.

## Fluxo de teste recomendado

```text
Commit de feature -> Pytest com mocks -> teste no PostgreSQL isolado
                  -> GitHub Actions verde -> merge develop -> main
```

Nunca remover volumes de banco persistente com `docker compose down -v` por conveniência.
