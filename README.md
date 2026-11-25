# FriendsMeeting

Projeto acadêmico de Raciocínio Algorítmico: aplicação de mensagens privadas com backend em Python (FastAPI), frontend web e persistência PostgreSQL.

## Funcionalidades

- Cadastro, login, renovação de sessão e recuperação de senha via authService.
- Perfil, código de amizade, convites, aceite/recusa e lista de amigos.
- Conversas privadas entre amigos, mensagens em tempo real via WebSocket, presença e reconexão com sincronização de mensagens.
- Histórico persistente, fotos de perfil e anexos de imagem (JPEG, PNG, WebP, até 5 MiB).
- Interface responsiva com temas claro e escuro.
- Testes Python com pytest e PostgreSQL isolado; verificações JavaScript e Playwright em GitHub Actions.

## Requisitos e instalação

Instale Git e Docker Desktop (Windows/macOS) ou Docker Engine com o plugin Compose (Linux). Inicie o Docker antes de executar os comandos. Não é necessário instalar Python, Node.js ou PostgreSQL diretamente para utilizar a aplicação.

Clone o repositório:

```bash
git clone https://github.com/rafael-mindahead/FriendsMeeting.git
cd FriendsMeeting
git switch main
```

Na raiz, copie `.env.example` para `.env` (no Windows PowerShell use `Copy-Item .env.example .env`; no macOS/Linux use `cp .env.example .env`). Se já existe um .env, preserve seus valores. Abra o arquivo e escolha valores para POSTGRES_USER, POSTGRES_PASSWORD e POSTGRES_DB. Use letras e números na senha local para evitar caracteres reservados em URLs. Os campos AUTH_* opcionais podem ficar como no exemplo. Não publique credenciais.

```bash
docker compose -f compose.yaml -f compose.frontend.yaml up -d --build --wait
docker compose -f compose.yaml -f compose.frontend.yaml ps
```

Abra **http://localhost:8081/app.html** para cadastro/login. A landing fica em http://localhost:8081 e a demonstração visual sem persistência em http://localhost:8081/app.html?demo=1. Documentação interativa: http://localhost:8000/docs. As migrations do banco são aplicadas automaticamente na inicialização. A primeira execução requer internet para baixar imagens e dependências.

### Demonstração funcional (dois usuários)

1. Abra a aplicação em dois navegadores ou janelas independentes; cadastre duas contas com e-mails distintos.
2. No perfil do segundo usuário, copie o código de amizade. No primeiro, envie um convite usando o código.
3. Aceite o convite na segunda conta e abra a conversa nas duas contas.
4. Envie mensagens e observe a entrega em tempo real e a presença; teste um anexo pequeno.
5. Recarregue, entre novamente e confira o histórico. Pare e reinicie os serviços (sem apagar volumes) para verificar persistência.

Para demonstrar entre dois computadores em uma rede local confiável (inclusive Wi-Fi fornecido pelo ESP32, se configurado separadamente), acrescente `FRONTEND_BIND_HOST=0.0.0.0` ao .env antes de iniciar e acesse `http://IP_DO_SERVIDOR:8081/app.html` no segundo computador. Autorize a porta 8081 no firewall local, se necessário. O FastAPI hospeda o WebSocket; este repositório não inclui firmware ESP32 nem funcionamento offline sem o backend. Não exponha a aplicação à internet.

### Diagnóstico e encerramento

```bash
docker compose -f compose.yaml -f compose.frontend.yaml logs --tail=100
docker compose -f compose.yaml -f compose.frontend.yaml stop
```

Se a porta 8081 ou 8000 estiver ocupada, libere-a antes de iniciar. Nunca use `down -v` se quiser conservar os dados. O banco de dados e os anexos novos ficam em volumes do Docker; arquivos enviados antes da montagem do volume não são migrados automaticamente.

## Arquitetura e dependências

Navegador → Nginx → FastAPI (HTTP + WebSocket) → PostgreSQL. O FastAPI consulta a API HTTP interna do authService; esta utiliza PostgreSQL próprio e Redis para autenticação. O ESP32 pode fornecer conectividade local, não substitui o servidor WebSocket Python.

Bibliotecas: FastAPI, Uvicorn, SQLAlchemy, psycopg, Alembic, Pydantic, httpx, Pillow e python-multipart; as dependências completas estão em [backend/requirements.txt](backend/requirements.txt) e [services/auth-service/requirements.txt](services/auth-service/requirements.txt). Frontend em HTML/CSS/JavaScript, servido por Nginx.

Veja [arquitetura e contratos](docs/ARCHITECTURE.md), [frontend](frontend/README.md) e [fotos](docs/AVATARS.md).

## Testes automatizados

Confira os resultados em [GitHub Actions](https://github.com/rafael-mindahead/FriendsMeeting/actions). Para testes locais, use Python 3.12 e PostgreSQL de teste isolado:

```bash
docker compose -p friendsmeeting-tests -f compose.test.yaml up -d --wait
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export FRIENDSMEETING_TEST_DATABASE_URL="postgresql+psycopg://test:test@127.0.0.1:5433/friendsmeeting_test"
export DATABASE_URL="$FRIENDSMEETING_TEST_DATABASE_URL"
python -m alembic upgrade head
python -m pytest tests/ -v
```

No Windows, use o Python do ambiente virtual e defina as variáveis equivalentes no PowerShell. Os testes de frontend são descritos em frontend/README.md. Não execute migrations de teste contra o banco principal.

## Limitações e entrega acadêmica

Aplicação para demonstração local; antes de produção são necessários TLS, controles adicionais de segurança e acesso privado a anexos. As imagens enviadas no chat e fotos públicas são acessíveis por URL a quem as possuir. A conexão WebSocket depende do backend ativo. Chamadas de voz/vídeo e firmware ESP32 não são comprovados nesta versão.

Os registros individuais devem ser PDFs revisados por cada integrante, com as três sprints, evidências reais e nomenclatura exigida pela professora. Consulte [orientação para os registros](registros_individuais/README.md) e [mapa da rubrica](docs/RUBRICA.md). As correções posteriores à apresentação ficam identificadas pelo histórico Git; não substituem contribuições ou evidências das sprints.
