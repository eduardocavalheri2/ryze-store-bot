KING STORE DISCORD BOT V2 - CORRIGIDO

O que foi corrigido:
- Compatibilidade com Render Web Service: servidor HTTP em 0.0.0.0:$PORT.
- Endpoint /health para health check do Render.
- Dockerfile corrigido.
- Variáveis de ambiente para token e ID opcional do servidor.
- Botões de compra persistentes com custom_id único por produto.
- Botões de pedido persistentes com custom_id único por pedido.
- Botões são restaurados automaticamente após reinício.
- /setup agora cria/encontra o canal da loja de verdade.
- Entrega por DM usando fetch_user.
- IDs, estoque e gravação do JSON mais seguros.
- /produto remover adicionado.
- Sincronização rápida dos slash commands quando DISCORD_GUILD_ID é informado.

RENDER
1. Suba os arquivos deste projeto para o repositório.
2. No Render, use Web Service e Docker.
3. Em Environment Variables, crie:
   DISCORD_TOKEN = token do seu bot
   DISCORD_GUILD_ID = ID do seu servidor (recomendado)
4. Health Check Path: /health
5. Deploy.

IMPORTANTE SOBRE O TOKEN:
Nunca coloque o token diretamente no GitHub. Use Environment Variables do Render.
Se o token já tiver sido publicado em algum lugar, gere um novo no Discord Developer Portal.

LOCAL
- Windows: execute start.bat
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

OBSERVAÇÃO SOBRE DADOS
O arquivo data.json é simples e funciona para testes. Em uma instância gratuita, o armazenamento local pode não ser permanente após determinados reinícios/redeploys. Para uma loja em produção, use um banco de dados externo ou armazenamento persistente.
