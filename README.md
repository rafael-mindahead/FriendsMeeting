
# FriendsMeeting

Plataforma de mensagens instantâneas desenvolvida com Python,
FastAPI e ESP32, utilizando comunicação em tempo real via WebSocket.

O projeto tem como diferencial o ESP32 atuando como servidor
intermediário das mensagens entre dispositivos conectados
à mesma rede local.

## Tecnologias

- Python 3.12
- FastAPI
- PostgreSQL 16
- Docker e Docker Compose
- HTML, CSS e JavaScript (planejado)
- ESP32 com C++ (planejado)
- WebSocket (planejado)

## Objetivo

Permitir que usuários criem contas, adicionem amigos e troquem
mensagens privadas em tempo real.

O sistema será utilizado inicialmente em uma rede Wi-Fi local,
compartilhada por um hotspot de celular.

## Funcionalidades planejadas

### Autenticação
- Cadastro de usuários
- Login e autenticação
- Perfil individual
- Código público único associado ao ID interno de cada usuário

### Amizades
- Busca de usuários pelo código público
- Envio de solicitações de amizade
- Aceitação e recusa de solicitações
- Notificações de solicitações recebidas
- Listagem de amigos

### Mensagens
- Conversas privadas entre amigos
- Mensagens em tempo real via WebSocket
- Histórico persistido no PostgreSQL
- Sem limite artificial de quantidade de mensagens
- ESP32 como intermediador da entrega das mensagens

## Arquitetura planejada

Frontend (HTML/CSS/JavaScript)
       |             |
       | HTTP        | WebSocket
       v             v
FastAPI            ESP32
       |             |
       |        Roteamento de
       |        mensagens em tempo real
       v
PostgreSQL

O FastAPI será responsável pelas contas, autenticação,
amizades e persistência dos dados.

O ESP32 será responsável pela comunicação WebSocket
e pelo encaminhamento de mensagens entre os clientes.

## Estrutura inicial

FriendsMeeting/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── compose.yaml
├── .env.example
├── .gitignore
└── README.md

## Executando o projeto

Requisitos:
- Docker
- Docker Compose

### 1. Clonar o repositório

git clone https://github.com/rafael-mindahead/FriendsMeeting.git

cd FriendsMeeting

### 2. Configurar ambiente

cp .env.example .env

Defina uma senha local segura em POSTGRES_PASSWORD.

### 3. Inicializar os serviços

docker compose up -d --build

### 4. Verificar o funcionamento

docker compose ps

curl http://localhost:8000/api/v1/health

### 5. Acessar a documentação da API

http://localhost:8000/docs

### 6. Testar PostgreSQL

docker compose exec db sh -c \
'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;"'

### 7. Encerrar os serviços

docker compose down

Não utilize docker compose down -v sem necessidade:
esse comando também remove os volumes de dados.

## Status do desenvolvimento

- [x] Inicialização do FastAPI
- [x] Dockerfile
- [x] Docker Compose
- [x] Contêiner PostgreSQL com healthcheck
- [x] Endpoint de health da API
- [ ] Conexão FastAPI/PostgreSQL
- [ ] Modelagem do banco
- [ ] Cadastro e login
- [ ] Gerenciamento de amizades
- [ ] Interface web
- [ ] Comunicação WebSocket
- [ ] Integração com ESP32
- [ ] Testes de integração ponta a ponta

## Evoluções futuras

Uma funcionalidade experimental será manter a troca
de mensagens entre usuários já conectados mesmo quando
o FastAPI ficar temporariamente indisponível.

Nesse cenário, a entrega em tempo real poderá continuar
pelo ESP32, mas autenticação, novos logins e persistência
dependerão de mecanismos adicionais.

## Organização do desenvolvimento

O projeto segue o método CRT:

1. Criar a funcionalidade.
2. Ler e revisar sua implementação.
3. Testar e validar seu comportamento.

Cada funcionalidade terá commits rastreáveis.

Branches:
- main: versão estável
- develop: integração de novas funcionalidades
- feature/*: desenvolvimento de funcionalidades específicas

## Segurança

O arquivo .env não deve ser versionado.

Senhas de usuários deverão ser armazenadas utilizando
hash seguro. As rotas e conexões de mensagens deverão
exigir autenticação e autorização.

A comunicação local não representa, por si só,
criptografia ponta a ponta.

## Licença

A licença do projeto ainda será definida.
