KING STORE DISCORD BOT V2 - 429 ROBUSTO

CORRECOES DESTA VERSAO
- Mantem o servidor HTTP em 0.0.0.0:$PORT para o Render.
- Endpoint /health para health check.
- Dockerfile incluido e pronto para Render Docker.
- Variaveis DISCORD_TOKEN e DISCORD_GUILD_ID via ambiente.
- Tratamento robusto de HTTP 429 no login/sincronizacao: le Retry-After quando disponivel.
- Se o Discord/Cloudflare nao enviar Retry-After, aguarda 15 minutos antes da nova tentativa.
- Backoff para erros 5xx e falhas temporarias de rede.
- Token invalido nao entra em loop: aparece claramente no log para corrigir no Render.
- Botoes persistentes de compra e pedidos.
- /setup cria/encontra o canal da loja.
- Entrega por DM usando fetch_user.
- /produto remover incluido.
- Slash commands sincronizados quando DISCORD_GUILD_ID e informado.

RENDER
1. Substitua os arquivos do repositorio por estes arquivos e faca commit/push.
2. No Render, abra o servico ryze-store-bot.
3. Se estiver usando Docker, o Render detectara o Dockerfile.
4. Confira Environment Variables:
   DISCORD_TOKEN = token do bot
   DISCORD_GUILD_ID = ID do seu servidor (recomendado)
5. Health Check Path: /health
6. Inicie um novo deploy do commit novo.

IMPORTANTE SOBRE O 429
O erro anterior mostrava HTTP 429 e a mensagem do Cloudflare/Discord pedindo cerca de 900 segundos antes de criar uma nova sessao. Esta versao nao encerra o processo quando isso acontece: ela mantem o health server ativo e espera o tempo indicado antes de tentar novamente.

Se o log mostrar 429, NAO fique clicando em deploy repetidamente. Deixe uma tentativa terminar. Deploys repetidos podem criar novas inicializacoes e prolongar o bloqueio.

TOKEN
Nunca coloque o token diretamente no GitHub. Use Environment Variables do Render.
Se o token foi exposto, gere outro no Discord Developer Portal.

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
O data.json e adequado para testes. Em uma instancia gratuita, armazenamento local pode nao ser permanente apos determinados reinicios/redeploys. Para producao, use banco externo ou armazenamento persistente.
