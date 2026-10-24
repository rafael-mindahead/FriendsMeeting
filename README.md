# FriendsMeeting

Chat local com ESP32 intermediando mensagens WebSocket entre notebooks.
O núcleo FastAPI do FriendsMeeting administra **perfis (UUID), códigos de
amizade e, futuramente, amizades e histórico**. Login, credenciais, tokens e
sessões são responsabilidades do [authService](https://github.com/rafael-mindahead/authService).

> Estado: **integração de autenticação em desenvolvimento**.
> A interface de chat, as amizades e o firmware do ESP32 ainda não estão prontos.

## Arquitetura

```text
Browser --HTTP--> FriendsMeeting API --> FriendsMeeting PostgreSQL (profiles)
                    |  |
                    |  +--HTTP (GET /auth/me)--> authService API
                    |                           |--> Auth PostgreSQL (accounts)
                    |                           +--> Redis (sessions/refresh)
Browser <-------- WebSocket ------------ ESP32 (planejado)
```

IDs no authService são **inteiros**. Cada perfil no FriendsMeeting tem um
**UUID local** e `auth_user_id` (inteiro único e opcional para contas antigas).
`friend_code` mantém o formato `FM-XXXXXXXX`. Tokens JWT não são
decodificados pelo FriendsMeeting: a validação é delegada ao authService
por meio de `/auth/me`.

Os perfis existentes do antigo cadastro local são preservados, inclusive os
respectivos UUIDs. **Não associamos automaticamente contas pelo e-mail.**
Perfis legados sem `auth_user_id` podem exigir uma migração assistida.

## Desenvolvimento local com Docker Desktop (Mac)

Você precisa ter **ambos os repositórios** clonados:

```bash
git clone https://github.com/rafael-mindahead/authService.git
git clone https://github.com/rafael-mindahead/FriendsMeeting.git
```

### 1. Inicie o authService

```bash
cd authService
git switch develop
git pull --ff-only origin develop
cp .env.example .env
# Edite as credenciais. Em SECRET_KEY, cole a saída de: openssl rand -hex 32
docker compose up -d --build
curl -i http://localhost:8001/health
```

O authService executa migrações com Alembic na inicialização da API.
A porta 8001 é usada para evitar conflito com o FriendsMeeting na 8000.
Mantenha o serviço restrito a um ambiente local de desenvolvimento.

### 2. Inicie o FriendsMeeting

```bash
cd ../FriendsMeeting
git switch develop
git pull --ff-only origin develop
# Se ainda não existir: cp .env.example .env
# Preserve as credenciais POSTGRES atuais (não remova o volume).
# No Docker Desktop, AUTH_SERVICE_URL=http://host.docker.internal:8001
docker compose up -d --build
docker compose exec api alembic upgrade head
curl -i http://localhost:8000/api/v1/health
```

Nunca use `docker compose down -v` para essa migração: removeria os dados.

### 3. Teste o fluxo (Swagger: http://localhost:8000/docs)

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"amigo_01","email":"amigo01@example.com","password":"SenhaDeTeste2026!"}'
```

O FriendsMeeting converte `username` para o campo `name` do authService
e grava um perfil local sem armazenar senha ou hash novo.

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"amigo01@example.com","password":"SenhaDeTeste2026!"}'
```

Use `access_token` retornado:

```bash
curl -i http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer COLE_SEU_ACCESS_TOKEN_AQUI"
```

Rotas proxy disponíveis: `/api/v1/auth/register`, `login`, `refresh`,
`logout`, `forgot-password`, `reset-password`; perfil em
`GET /api/v1/users/me`. O serviço de autenticação deve estar acessível.

Se o cadastro remoto funcionar mas o banco do FriendsMeeting falhar,
o **próximo login** tenta provisionar o perfil novamente. Uma conta legada
com e-mail idêntico **não será vinculada automaticamente**; trate o conflito
explicitamente antes de continuar.

## Testes

No FriendsMeeting:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

A suíte de integração HTTP usa mocks e **não exige authService rodando**.
O GitHub Actions repete os testes na branch `develop` e em pull requests.

**Atenção ao authService:** sua suíte de testes apaga e recria tabelas.
Execute-a somente com `.env.test`, apontando a banco dedicado com sufixo
`_test` e Redis DB `/1`.

## Próximas entregas

- [x] Docker, PostgreSQL, SQLAlchemy, Alembic e tabela de perfis
- [x] Cliente HTTP para authService, rotas proxy e vínculo por `auth_user_id`
- [ ] Validar o fluxo completo entre os dois projetos no Mac
- [ ] Solicitações de amizade e notificações de eventos
- [ ] Persistência de mensagens e histórico
- [ ] Firmware ESP32 WebSocket e testes via hotspot do celular
- [ ] Interface web de login, amigos e chat

## Segurança

O authService mantém credenciais, JWT e refresh tokens. O FriendsMeeting não
deve compartilhar seu `SECRET_KEY` nem confiar em IDs enviados pelo navegador.
`.env` nunca entra no Git. Antes de disponibilizar o sistema fora da rede
controlada, configurar HTTPS/WSS, políticas CORS, limites de taxa e observabilidade.

### Método CRT

Criar, Ler e Testar, mantendo commits rastreáveis na `develop`. A `main`
recebe somente alterações validadas.
