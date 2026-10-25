# FriendsMeeting

Plataforma de conversas privadas em desenvolvimento, com **FastAPI**, **PostgreSQL**, **Docker Compose** e autenticação delegada ao **authService**. O objetivo futuro é permitir comunicação em rede local via **WebSocket/ESP32**, inclusive em um cenário com o backend temporariamente indisponível.

> **Estado atual:** o backend HTTP para cadastro/login, perfis, amizades, conversas e mensagens está implementado. **WebSocket, firmware do ESP32 e interface web ainda não estão implementados.** Não confunda as APIs HTTP existentes com um chat em tempo real pronto.

## Funcionalidades disponíveis

- Cadastro, login, refresh, logout e recuperação de senha por proxy para o authService.
- Perfil local UUID, associado ao identificador inteiro do authService por `auth_user_id`.
- Código de amizade único no formato `FM-XXXXXXXX`, solicitações, aceite, recusa, reenvio e listagem de amigos.
- Conversa privada única por par de amigos; criação idempotente (201 nova / 200 existente).
- Envio de mensagens textuais de **1 a 2.000 caracteres**, rejeitando conteúdo só com espaços.
- Histórico persistente, ordenado por data/ID decrescentes, com `limit` (1–100, padrão 20) e `offset` (padrão 0).
- Autorização por participante: usuários externos não conseguem consultar nem enviar mensagens em conversas alheias.
- Testes unitários e testes de integração em **PostgreSQL separado**, com CI no GitHub Actions.

## Arquitetura

```text
Navegador / cliente HTTP
       |
       v
FriendsMeeting FastAPI (:8000) ----HTTP interno----> authService FastAPI (:8001 no host)
       |                                            |               |
       v                                            v               v
PostgreSQL FriendsMeeting                  PostgreSQL auth       Redis auth
(users, friend_requests,
 conversations, messages)

[Futuro] Navegadores <-- WebSocket local --> ESP32 (sem API Python ativa)
```

O FriendsMeeting **não valida JWT por conta própria**: encaminha o token a `GET /auth/me` do authService e provisiona o perfil local com UUID. Credenciais e sessões pertencem ao authService. Perfis legados não são vinculados silenciosamente apenas por e-mail.

O projeto possui **um único** `compose.yaml` para as duas APIs, dois bancos PostgreSQL e o Redis. Não é preciso clonar o authService separadamente para rodar esta versão; seu código está em `services/auth-service/`.

Detalhes adicionais: [arquitetura e contratos HTTP](docs/ARCHITECTURE.md).

## Preparação local (macOS / Linux)

Requisitos: Docker Desktop/Engine, Docker Compose e Git. Para os testes locais fora dos contêineres, Python 3.12+.

```bash
git clone https://github.com/rafael-mindahead/FriendsMeeting.git
cd FriendsMeeting
git switch develop
cp .env.example .env
```

Edite `.env` definindo **POSTGRES_USER, POSTGRES_PASSWORD e POSTGRES_DB**. Para a autenticação, `AUTH_POSTGRES_*` pode ser definido separadamente; em desenvolvimento local o Compose possui padrões. Uma chave `AUTH_SECRET_KEY` explícita é recomendada para ambientes persistentes; sem ela, o serviço pode gerar e persistir uma no volume `auth_config`.

**Não sobrescreva** seu `.env` existente nem remova volumes de bancos já configurados.

```bash
docker compose up -d --build
docker compose ps

curl -f http://localhost:8000/api/v1/health
curl -f http://localhost:8001/health
```

- FriendsMeeting Swagger: <http://localhost:8000/docs>
- authService Swagger: <http://localhost:8001/docs>
- As migrations são aplicadas no início da API (`alembic upgrade head`).
- O authService pode levar alguns segundos para ficar saudável no primeiro início.

**Nunca use `docker compose down -v`** em um ambiente com dados que deseja preservar: o comando apaga os volumes do Compose.

## Exemplo do fluxo HTTP

### 1. Cadastro e login

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice_01","email":"alice01@example.com","password":"SenhaDeTeste2026!"}'

curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice01@example.com","password":"SenhaDeTeste2026!"}'
```

Use o `access_token` do login nas chamadas autenticadas:

```bash
curl -H "Authorization: Bearer SEU_TOKEN" \
  http://localhost:8000/api/v1/users/me
```

### 2. Amizades, conversa e mensagens

- `POST /api/v1/friends/requests` com `{"friend_code":"FM-XXXXXXXX"}`.
- `GET /api/v1/friends/requests` lista solicitações recebidas pendentes.
- `PATCH /api/v1/friends/requests/{id}` com `{"action":"accept"}` ou `{"action":"reject"}`.
- `GET /api/v1/friends` lista amigos aceitos.
- `POST /api/v1/conversations` com `{"friend_id":"UUID_DO_AMIGO"}`.
- `GET /api/v1/conversations` lista conversas próprias.
- `GET /api/v1/conversations/{id}` consulta uma conversa própria.
- `POST /api/v1/conversations/{id}/messages` com `{"body":"Olá!"}`.
- `GET /api/v1/conversations/{id}/messages?limit=20&offset=0` consulta o histórico.

Toda rota de amizades, conversas e mensagens exige `Authorization: Bearer`, validado pelo authService. A mensagem não é enviada instantaneamente ao outro navegador ainda; o histórico é consultado via HTTP.

## Testes: mocks e PostgreSQL real

A execução completa usa o banco `friendsmeeting_test` na porta local **5433**, isolado do banco principal. Os testes de integração abrem transações que são revertidas ao final de cada caso. Não execute as migrations de testes apontando para o banco principal.

Na raiz do repositório:

```bash
docker compose -p friendsmeeting-tests -f compose.test.yaml up -d --wait
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Aplique as migrations no banco de testes:

```bash
export FRIENDSMEETING_TEST_DATABASE_URL="postgresql+psycopg://test:test@127.0.0.1:5433/friendsmeeting_test"
DATABASE_URL="$FRIENDSMEETING_TEST_DATABASE_URL" python -m alembic upgrade head
DATABASE_URL="$FRIENDSMEETING_TEST_DATABASE_URL" python -m pytest tests/ -v
```

Para executar apenas os testes com mocks:

```bash
python -m pytest tests/test_messages.py tests/test_conversations.py -v
```

O [workflow de CI](.github/workflows/backend-tests.yml) provisiona o PostgreSQL temporário, aplica migrations e executa a suíte completa a cada push em `develop`/`main` e em pull requests. A suíte do authService vendorizado é independente; consulte `services/auth-service/README.md` para o ambiente específico de testes desse serviço.

## Próximas entregas

- [x] Docker Compose unificado, PostgreSQL, Redis e migrations
- [x] Autenticação delegada, perfis e códigos de amizade
- [x] Solicitações de amizade, aceite, recusa e listagem
- [x] Conversas privadas e histórico persistente
- [x] Testes automatizados de API e integração PostgreSQL
- [ ] WebSocket autenticado, presença e notificações em tempo real
- [ ] Integração ESP32 e testes entre dois notebooks em rede local
- [ ] Interface web responsiva
- [ ] Estratégia de sincronização offline, robustez e observabilidade

## Segurança e cuidados

Nunca versione `.env`, credenciais ou `AUTH_SECRET_KEY`. O Compose é direcionado a desenvolvimento local; antes de expor o serviço publicamente, configurar TLS/HTTPS/WSS, CORS restrito, limites de taxa, logs de auditoria e política de retenção. `HTTP 404` oculta a existência de conversas de outros usuários. Os testes automatizados não substituem uma auditoria de segurança externa.

### Método CRT e branches

Desenvolvimento incremental em `develop`: **Criar, Ler e Testar**; a `main` recebe marcos validados, preservando o histórico. A branch de trabalho contínuo continua sendo `develop`.

**Licenciamento:** ainda não há arquivo de licença declarado neste repositório; antes de redistribuir ou receber contribuições externas, definir uma licença e registrar atribuições.
