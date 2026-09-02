import asyncio
import json
import logging
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
DB = Path(os.getenv("DATA_FILE", "data.json"))

DEFAULT_DB = {"products": [], "orders": [], "settings": {}}
DB_LOCK = threading.RLock()

# Evita que logs da biblioteca escondam o erro real no Render.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("king-store")


def load_db() -> dict[str, Any]:
    with DB_LOCK:
        if not DB.exists():
            save_db(DEFAULT_DB.copy())
        try:
            data = json.loads(DB.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Não foi possível ler data.json (%s). Criando banco vazio.", exc)
            data = {
                "products": [],
                "orders": [],
                "settings": {},
            }
            save_db(data)
        data.setdefault("products", [])
        data.setdefault("orders", [])
        data.setdefault("settings", {})
        return data


def save_db(data: dict[str, Any]) -> None:
    with DB_LOCK:
        DB.parent.mkdir(parents=True, exist_ok=True)
        temp = DB.with_suffix(".tmp")
        temp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(DB)


def is_admin(interaction: discord.Interaction) -> bool:
    return bool(
        interaction.guild
        and interaction.user
        and interaction.user.guild_permissions.administrator
    )


def new_id() -> str:
    return secrets.token_hex(4).upper()


def money(value: float) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in ("/", "/health"):
            self.send_response(404)
            self.end_headers()
            return

        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        return


def start_health_server() -> ThreadingHTTPServer:
    # Render espera o processo ouvindo em 0.0.0.0 e na porta PORT.
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    thread = threading.Thread(
        target=server.serve_forever,
        name="render-health",
        daemon=True,
    )
    thread.start()
    log.info("HTTP health server listening on 0.0.0.0:%s", PORT)
    return server


class BuyButton(discord.ui.Button):
    def __init__(self, product_id: str):
        super().__init__(
            label="Comprar",
            emoji="🛒",
            style=discord.ButtonStyle.success,
            custom_id=f"ks:buy:{product_id}",
        )
        self.product_id = product_id

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ Este botão só funciona dentro do servidor.",
                ephemeral=True,
            )

        data = load_db()
        product = next(
            (p for p in data["products"] if p.get("id") == self.product_id),
            None,
        )
        if not product or not product.get("stock"):
            return await interaction.response.send_message(
                "❌ Produto sem estoque.",
                ephemeral=True,
            )

        category = discord.utils.get(
            interaction.guild.categories,
            name="🛒 COMPRAS",
        )
        if category is None:
            category = await interaction.guild.create_category("🛒 COMPRAS")

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            ),
        }

        channel_name = f"pedido-{interaction.user.name}"[:90]
        channel = await interaction.guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Pedido da King Store - {interaction.user.id}",
        )

        order_id = new_id()
        data["orders"].append(
            {
                "id": order_id,
                "user": interaction.user.id,
                "product": product["id"],
                "channel": channel.id,
                "status": "aguardando",
            }
        )
        save_db(data)

        embed = discord.Embed(
            title="🛒 Pedido criado",
            description=(
                f"**{product['name']}**\n"
                f"💰 **{money(float(product['price']))}**\n\n"
                f"Pedido: `{order_id}`"
            ),
            color=0x7C3AED,
        )
        await channel.send(
            interaction.user.mention,
            embed=embed,
            view=OrderView(order_id),
        )
        await interaction.response.send_message(
            f"✅ Pedido aberto: {channel.mention}",
            ephemeral=True,
        )


class BuyView(discord.ui.View):
    def __init__(self, product_id: str):
        super().__init__(timeout=None)
        self.add_item(BuyButton(product_id))


class ConfirmButton(discord.ui.Button):
    def __init__(self, order_id: str):
        super().__init__(
            label="Confirmar pagamento",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"ks:confirm:{order_id}",
        )
        self.order_id = order_id

    async def callback(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True,
            )

        data = load_db()
        order = next(
            (o for o in data["orders"] if o.get("id") == self.order_id),
            None,
        )
        if not order:
            return await interaction.response.send_message(
                "❌ Pedido não encontrado.",
                ephemeral=True,
            )
        if order.get("status") == "entregue":
            return await interaction.response.send_message(
                "⚠️ Este pedido já foi entregue.",
                ephemeral=True,
            )
        if order.get("status") == "fechado":
            return await interaction.response.send_message(
                "⚠️ Este pedido está fechado.",
                ephemeral=True,
            )

        product = next(
            (p for p in data["products"] if p.get("id") == order.get("product")),
            None,
        )
        if not product or not product.get("stock"):
            return await interaction.response.send_message(
                "❌ Estoque vazio.",
                ephemeral=True,
            )

        item = product["stock"].pop(0)
        order["status"] = "entregue"
        order["delivered_item"] = item
        save_db(data)

        try:
            user = await interaction.client.fetch_user(int(order["user"]))
            await user.send(
                f"📦 **Entrega do pedido {self.order_id}**\n\n`{item}`"
            )
        except (discord.Forbidden, discord.NotFound):
            return await interaction.response.send_message(
                "⚠️ Pedido marcado como entregue, mas não consegui enviar DM ao cliente. "
                "Confira as configurações de privacidade dele.",
                ephemeral=True,
            )

        await interaction.response.send_message(
            "✅ Pagamento confirmado e produto enviado por DM.",
            ephemeral=True,
        )


class CloseButton(discord.ui.Button):
    def __init__(self, order_id: str):
        super().__init__(
            label="Fechar",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id=f"ks:close:{order_id}",
        )
        self.order_id = order_id

    async def callback(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True,
            )

        data = load_db()
        order = next(
            (o for o in data["orders"] if o.get("id") == self.order_id),
            None,
        )
        if order and order.get("status") == "aguardando":
            order["status"] = "fechado"
            save_db(data)

        await interaction.response.send_message(
            "🔒 Pedido fechado.",
            ephemeral=True,
        )
        try:
            await interaction.channel.delete(
                reason=f"Pedido {self.order_id} fechado"
            )
        except discord.HTTPException:
            pass


class OrderView(discord.ui.View):
    def __init__(self, order_id: str):
        super().__init__(timeout=None)
        self.add_item(ConfirmButton(order_id))
        self.add_item(CloseButton(order_id))


class SetupModal(discord.ui.Modal, title="Configuração da King Store"):
    channel_name = discord.ui.TextInput(
        label="Nome do canal da loja",
        default="🛍️・loja",
        max_length=90,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ Use este comando dentro de um servidor.",
                ephemeral=True,
            )

        name = str(self.channel_name).strip()
        channel = discord.utils.get(
            interaction.guild.text_channels,
            name=name,
        )
        if channel is None:
            channel = await interaction.guild.create_text_channel(
                name,
                reason="Configuração da King Store",
            )

        data = load_db()
        data["settings"][str(interaction.guild.id)] = {
            "store_channel": channel.id,
            "name": name,
        }
        save_db(data)
        await interaction.response.send_message(
            f"✅ Loja configurada em {channel.mention}. Agora use `/produto criar` e `/painel`.",
            ephemeral=True,
        )


class KingStoreBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.commands_synced = False

    async def sync_commands(self) -> None:
        """Sincroniza slash commands sem derrubar o bot se o Discord retornar 429."""
        try:
            if GUILD_ID.isdigit():
                guild = discord.Object(id=int(GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info(
                    "Slash commands sincronizados no servidor %s: %s",
                    GUILD_ID,
                    len(synced),
                )
            else:
                synced = await self.tree.sync()
                log.info("Slash commands globais sincronizados: %s", len(synced))
            self.commands_synced = True
        except discord.HTTPException as exc:
            log.warning(
                "Não foi possível sincronizar os slash commands agora (HTTP %s). "
                "O bot continuará online e tentará novamente.",
                exc.status,
            )
        except Exception:
            log.exception("Erro inesperado ao sincronizar slash commands.")

    async def setup_hook(self):
        data = load_db()

        # Reativa botões persistentes após reinícios.
        for product in data["products"]:
            if product.get("id"):
                self.add_view(BuyView(product["id"]))

        for order in data["orders"]:
            if order.get("id") and order.get("status") == "aguardando":
                self.add_view(OrderView(order["id"]))

        # Um 429 aqui não pode impedir o bot de conectar.
        await self.sync_commands()


bot = KingStoreBot()


@bot.event
async def on_ready():
    log.info("King Store V2 online como %s (ID %s)", bot.user, bot.user.id)
    if not bot.commands_synced:
        await bot.sync_commands()


@bot.tree.command(name="setup", description="Configura a loja sem editar o código")
async def setup(interaction: discord.Interaction):
    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ Apenas administradores.",
            ephemeral=True,
        )
    await interaction.response.send_modal(SetupModal())


produto = app_commands.Group(
    name="produto",
    description="Gerenciar produtos",
)


@produto.command(name="criar", description="Criar produto")
@app_commands.describe(
    nome="Nome do produto",
    preco="Preço em reais",
    descricao="Descrição do produto",
)
async def criar(
    interaction: discord.Interaction,
    nome: str,
    preco: float,
    descricao: str = "",
):
    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ Sem permissão.",
            ephemeral=True,
        )
    if preco < 0:
        return await interaction.response.send_message(
            "❌ O preço não pode ser negativo.",
            ephemeral=True,
        )
    if not nome.strip():
        return await interaction.response.send_message(
            "❌ O nome não pode estar vazio.",
            ephemeral=True,
        )

    data = load_db()
    product = {
        "id": new_id(),
        "name": nome.strip()[:100],
        "price": round(preco, 2),
        "description": descricao.strip()[:1000],
        "stock": [],
    }
    data["products"].append(product)
    save_db(data)
    bot.add_view(BuyView(product["id"]))
    await interaction.response.send_message(
        f"✅ Produto criado: `{product['id']}`",
        ephemeral=True,
    )


@produto.command(name="estoque", description="Adicionar item/key ao estoque")
@app_commands.describe(id="ID do produto", item="Key ou conteúdo para entregar")
async def estoque(interaction: discord.Interaction, id: str, item: str):
    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ Sem permissão.",
            ephemeral=True,
        )

    data = load_db()
    product = next(
        (p for p in data["products"] if p.get("id", "").upper() == id.upper()),
        None,
    )
    if not product:
        return await interaction.response.send_message(
            "❌ Produto não encontrado.",
            ephemeral=True,
        )
    if not item.strip():
        return await interaction.response.send_message(
            "❌ O item não pode estar vazio.",
            ephemeral=True,
        )

    product.setdefault("stock", []).append(item.strip())
    save_db(data)
    await interaction.response.send_message(
        "✅ Item adicionado ao estoque.",
        ephemeral=True,
    )


@produto.command(name="listar", description="Listar produtos")
async def listar(interaction: discord.Interaction):
    data = load_db()
    if not data["products"]:
        return await interaction.response.send_message(
            "Nenhum produto cadastrado.",
            ephemeral=True,
        )
    text = "\n".join(
        f"`{p['id']}` • **{p['name']}** • {money(float(p['price']))} • {len(p.get('stock', []))} em estoque"
        for p in data["products"]
    )
    await interaction.response.send_message(text[:1900], ephemeral=True)


@produto.command(name="remover", description="Remover produto")
@app_commands.describe(id="ID do produto")
async def remover(interaction: discord.Interaction, id: str):
    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ Sem permissão.",
            ephemeral=True,
        )
    data = load_db()
    before = len(data["products"])
    data["products"] = [
        p for p in data["products"]
        if p.get("id", "").upper() != id.upper()
    ]
    if len(data["products"]) == before:
        return await interaction.response.send_message(
            "❌ Produto não encontrado.",
            ephemeral=True,
        )
    save_db(data)
    await interaction.response.send_message(
        "✅ Produto removido.",
        ephemeral=True,
    )


bot.tree.add_command(produto)


@bot.tree.command(name="painel", description="Publicar o catálogo da loja")
async def painel(interaction: discord.Interaction):
    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ Sem permissão.",
            ephemeral=True,
        )
    if not interaction.guild:
        return await interaction.response.send_message(
            "❌ Use este comando dentro de um servidor.",
            ephemeral=True,
        )

    data = load_db()
    settings = data["settings"].get(str(interaction.guild.id), {})
    target = interaction.guild.get_channel(settings.get("store_channel"))
    if not isinstance(target, discord.TextChannel):
        target = interaction.channel

    if not data["products"]:
        return await interaction.response.send_message(
            "❌ Nenhum produto cadastrado.",
            ephemeral=True,
        )

    for product in data["products"]:
        embed = discord.Embed(
            title="🛍️ " + product["name"],
            description=product["description"] or "Produto digital",
            color=0x7C3AED,
        )
        embed.add_field(
            name="💰 Preço",
            value=money(float(product["price"])),
            inline=True,
        )
        embed.add_field(
            name="📦 Estoque",
            value=str(len(product.get("stock", []))),
            inline=True,
        )
        embed.set_footer(text=f"ID: {product['id']} • King Store")
        await target.send(
            embed=embed,
            view=BuyView(product["id"]),
        )

    await interaction.response.send_message(
        f"✅ Painel publicado em {target.mention}.",
        ephemeral=True,
    )


@bot.tree.command(name="pedidos", description="Ver os últimos pedidos")
async def pedidos(interaction: discord.Interaction):
    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ Sem permissão.",
            ephemeral=True,
        )
    data = load_db()
    orders = data["orders"][-20:]
    text = "\n".join(
        f"`{o['id']}` • <@{o['user']}> • `{o['status']}` • produto `{o['product']}`"
        for o in orders
    ) or "Nenhum pedido."
    await interaction.response.send_message(text[:1900], ephemeral=True)


@bot.tree.command(name="gerarkey", description="Gera uma key aleatória")
async def gerarkey(interaction: discord.Interaction):
    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ Sem permissão.",
            ephemeral=True,
        )
    key = "KS-" + "-".join(
        "".join(
            secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
            for _ in range(5)
        )
        for _ in range(3)
    )
    await interaction.response.send_message(
        f"🔑 `{key}`",
        ephemeral=True,
    )


async def run_bot_with_retry() -> None:
    """Inicia o bot e trata 429/Cloudflare sem entrar em loop agressivo."""
    if not TOKEN or TOKEN == "COLE_O_TOKEN_AQUI":
        raise RuntimeError(
            "Configure a variável de ambiente DISCORD_TOKEN no Render."
        )

    attempt = 0
    while True:
        try:
            attempt += 1
            log.info("Conectando ao Discord (tentativa %s)...", attempt)
            await bot.start(TOKEN, reconnect=True)
            # start() normalmente só retorna após close() / encerramento.
            log.warning("Conexão com o Discord foi encerrada.")
            attempt = 0
        except discord.LoginFailure:
            log.exception(
                "Falha de login no Discord. Verifique DISCORD_TOKEN. "
                "Um token inválido não será repetido automaticamente."
            )
            raise
        except discord.HTTPException as exc:
            if exc.status == 429:
                # O Discord/Cloudflare pediu para reduzir a frequência.
                # O limite é deliberadamente conservador para evitar outro bloqueio.
                wait = min(300, max(30, 30 * (2 ** min(attempt - 1, 3))))
                log.error(
                    "Discord respondeu HTTP 429 (Too Many Requests). "
                    "Aguardando %ss antes de tentar novamente.",
                    wait,
                )
                await bot.close()
                await asyncio.sleep(wait)
                continue

            log.exception("Discord retornou HTTP %s.", exc.status)
            await bot.close()
            await asyncio.sleep(15)
        except (discord.GatewayNotFound, discord.ConnectionClosed) as exc:
            wait = min(120, max(10, 10 * max(1, attempt)))
            log.warning(
                "Conexão com o Gateway caiu (%s). Nova tentativa em %ss.",
                exc,
                wait,
            )
            await bot.close()
            await asyncio.sleep(wait)
        except (OSError, asyncio.TimeoutError) as exc:
            wait = min(120, max(10, 10 * max(1, attempt)))
            log.warning(
                "Erro de rede (%s). Nova tentativa em %ss.",
                exc,
                wait,
            )
            await bot.close()
            await asyncio.sleep(wait)
        except Exception:
            log.exception(
                "Erro inesperado ao iniciar/manter o bot. Nova tentativa em 30s."
            )
            await bot.close()
            await asyncio.sleep(30)


async def main():
    health_server = start_health_server()
    try:
        await run_bot_with_retry()
    finally:
        health_server.shutdown()
        health_server.server_close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Encerrado pelo usuário.")
