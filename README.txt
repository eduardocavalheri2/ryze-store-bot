KING STORE DISCORD BOT - RENDER 429 ROBUST FIX

Este pacote mantém a versão da loja e corrige o problema observado no Render:
HTTP 429 (Too Many Requests) seguido por "RuntimeError: Session is closed".

O QUE FOI CORRIGIDO
- Tratamento robusto de HTTP 429 do Discord/Cloudflare.
- Leitura de Retry-After quando o servidor fornece esse cabeçalho.
- Backoff exponencial com jitter para evitar novas tentativas em sequência.
- A sessão HTTP fechada não é reutilizada.
- Em falhas de conexão, o processo é reiniciado de forma limpa para criar uma nova sessão aiohttp.
- Servidor HTTP em 0.0.0.0:$PORT para o Render.
- Endpoint /health para health check.
- Sincronização dos slash commands protegida contra 429.
- Botões persistentes restaurados após reinício.
- Banco JSON mantido no mesmo formato.

IMPORTANTE SOBRE O TOKEN
NUNCA coloque o token do bot no código ou no GitHub.
Use somente a variável DISCORD_TOKEN no Render.

Se o token foi exposto em código, chat, print ou repositório, considere-o comprometido:
1. Gere um novo token no Discord Developer Portal.
2. No Render, abra Environment -> Environment Variables.
3. Substitua DISCORD_TOKEN pelo novo token.
4. Salve e faça um novo deploy.

RENDER
1. Substitua os arquivos do repositório pelos arquivos deste ZIP.
2. Faça commit/push para a branch usada pelo serviço.
3. No Render, abra o serviço ryze-store-bot.
4. Vá em Deploys e use "Deploy latest commit" (ou aguarde o deploy automático).
5. Health Check Path: /health.
6. Confira os Logs.

Se aparecer HTTP 429 novamente, o bot agora espera antes de tentar e cria uma sessão HTTP nova.
Não fique apertando Deploy repetidamente: isso pode gerar novas tentativas de conexão e aumentar o rate limit.

VARIÁVEIS
DISCORD_TOKEN = token atual do bot
DISCORD_GUILD_ID = ID do servidor (recomendado)
PORT = fornecida automaticamente pelo Render
DATA_FILE = opcional; padrão data.json

LOCAL
Windows: execute start.bat
Ou: pip install -r requirements.txt && python bot.py

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
O arquivo data.json funciona para testes. Em uma instância gratuita, o armazenamento local pode não ser permanente após determinados reinícios/redeploys. Para uma loja em produção, use banco de dados externo ou armazenamento persistente.
