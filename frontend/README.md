# FriendsMeeting — Frontend

Interface com inspiração Apple, HTML sem frameworks, CSS em camadas, JavaScript ES modules e Nginx.

## Executar

Na raiz do repositório, configure o .env principal seguindo o README:

```bash
docker compose -f compose.yaml -f compose.frontend.yaml up -d --build
docker compose -f compose.yaml -f compose.frontend.yaml ps
```

Acesse **http://localhost:8081** para a landing, **http://localhost:8081/app.html** para login/cadastro e **http://localhost:8081/app.html?demo=1** para testar o layout sem conta.

## Rotas e telas

- **Entrar / cadastro:** `/app.html?mode=login` e `/app.html?mode=register`, ligados a `/api/v1/auth`.
- **Chat:** mensagens via WebSocket, estado online, reconexão com backoff e recuperação com cursor.
- **Amigos:** convites por código, aceite/recusa e abertura da conversa.
- **Meu perfil:** foto própria (2 MiB; PNG/JPG/WebP), nome, e-mail e código de amizade.
- **Fotos de outros usuários:** carregadas da rota pública `/api/v1/users/{user_id}/avatar`, com fallback por iniciais.
- **Configurações:** modo claro, escuro e automático, escolha salva no navegador.

O tema é armazenado no `localStorage`; tokens não são persistidos. Após atualizar a página, entre novamente. As fotos ficam no PostgreSQL; a foto é **pública** para quem possuir seu URL/identificador. Veja `docs/AVATARS.md` para limitações de privacidade.

## Desenvolvimento

Arquivos estáticos em `frontend/`; nenhuma instalação npm é necessária para servir. Para executar os testes:

```bash
cd frontend
npm test
find js -name '*.js' -exec node --check {} \;
```

A ação `frontend-tests.yml` valida sintaxe e testes. A ação do backend continua responsável por migrations e pytest.

## Observações

A integração com ESP32 não foi implementada nesta entrega. Não usar o Compose local como ambiente público sem TLS, rate limiting, autenticação revalidada no WebSocket e observabilidade. A interface de demonstração não persiste dados.

## Método CRT

Mudanças em `develop`, separadas por responsabilidade para permitir criação, leitura e teste. Promover para `main` somente após aprovação da validação.

## Auditoria UI Humanizer (2026-11-01)

A direção de design e as decisões estão em [DESIGN.md](./DESIGN.md). O projeto preserva a identidade verde/grafite, mas remove textos genéricos de marketing, depoimentos simulados, ícones de emoji e reconstruções do compositor por eventos. O histórico é carregado em páginas de 40 mensagens, com preservação da posição de leitura; convites mostram remetente e foto.

A CI também verifica a interface em **1440×900, 768×1024 e 390×844** com Playwright. Execução local:

```bash
cd frontend
npm install
npx playwright install chromium
npm run test:e2e
```

A recuperação de login após reload ainda exige suporte a cookies HttpOnly do backend; a paginação anterior do histórico passou a usar `before_id`, preservando clientes que usam `offset`. A atualização manual de conversas preserva texto, foco e cursor de digitação. A captura ilustrativa da landing deve ser trocada por screenshot real aprovado antes da publicação final.
