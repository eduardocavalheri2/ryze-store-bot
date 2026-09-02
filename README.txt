KING STORE DISCORD BOT V3 - RENDER FIX

Esta versão mantém as funções da V2 e corrige o principal problema visto no Render:
- HTTP health server em 0.0.0.0:$PORT.
- /health aceita também query strings.
- Erros HTTP 429 do Discord não derrubam imediatamente o processo.
- Backoff conservador para 429/Cloudflare antes de nova tentativa.
- Falhas de sincronização dos slash commands não impedem o bot de conectar.
- Slash commands são tentados novamente no on_ready quando necessário.
- LoginFailure (token inválido) é mostrado claramente em vez de criar loop infinito.
- Reconexões de Gateway/rede recebem espera progressiva.
- Persistência dos botões continua funcionando.
- data.json é protegido contra gravação parcial.

RENDER
1. Substitua os arquivos do repositório pelos arquivos deste ZIP.
2. No Render, mantenha o serviço como Web Service + Docker.
3. Em Environment Variables, configure:
   DISCORD_TOKEN = token real do seu bot
   DISCORD_GUILD_ID = ID do seu servidor (recomendado)
4. Health Check Path: /health
5. Faça apenas um novo Deploy depois de substituir os arquivos.
6. Se aparecer HTTP 429, NÃO fique reiniciando manualmente. Esta versão espera e tenta novamente.

IMPORTANTE SOBRE O TOKEN
Nunca coloque o token real no GitHub.
Se o token já foi exposto, gere outro no Discord Developer Portal.
O arquivo .env.example contém apenas um placeholder.

DOCKER
O Dockerfile usa Python 3.12, instala requirements.txt e inicia bot.py.
O Render define PORT automaticamente.

LOCAL
- Edite uma cópia de .env.example para .env e coloque o token.
- Execute start.bat.
- Ou: pip install -r requirements.txt && python bot.py

COMANDOS
/setup
/produto criar
/produto estoque
/produto listar
/produto remover
/painel
/pedidos
/gerarkey

DADOS
O data.json é armazenamento local simples para testes. No plano gratuito do Render,
o armazenamento local pode não ser permanente depois de determinados reinícios/redeploys.
Para produção, use armazenamento persistente ou banco de dados externo.
