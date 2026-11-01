# Fotos de perfil — FriendsMeeting

O usuário autenticado pode escolher ou remover sua foto. As fotos ficam em uma tabela própria no PostgreSQL (migração f7b2c31d904e), sobrevivem ao reinício do contêiner e são excluídas automaticamente quando o usuário é excluído.

## Contratos

- `PUT /api/v1/users/me/avatar` com `multipart/form-data`, campo `file`; requer Bearer. Retorna `avatar_url` e `revision`.
- `DELETE /api/v1/users/me/avatar` requer Bearer. Retorna 204, inclusive se não houver foto.
- `GET /api/v1/users/{user_id}/avatar` é público por escolha de produto; entrega WebP ou 404.

## Segurança

- Máximo 2 MiB por upload; PNG, JPG e WebP válidos; limite de 12 MP de imagem original.
- Reamostra para 320 × 320 WebP; descarta metadados EXIF/GPS. Não aceita SVG nem GIF.
- Somente o proprietário pode adicionar/remover a foto.
- A foto é **pública** para qualquer pessoa que tenha o ID/URL: evite informações sensíveis. Adicione controles de privacidade antes de expor amplamente.
- Contém binários em PostgreSQL. Para muitos usuários, migrar a mídia para object storage, com verificação de conteúdo e política de retenção.
- Não confundir `localhost:8000` (API principal) com `localhost:8001` (authService).

## Testes

`pytest tests/test_avatars.py tests/test_avatar_model.py tests/test_avatar_security.py -v`

As migrations são executadas no arranque da API. Em testes use **somente** `friendsmeeting_test` na porta 5433.
