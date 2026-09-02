import os, json, secrets, discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
load_dotenv()
TOKEN=os.getenv("DISCORD_TOKEN")
DB="data.json"
def load():
    if not os.path.exists(DB):
        save({"products":[],"orders":[],"settings":{}})
    return json.load(open(DB,encoding="utf8"))
def save(x): json.dump(x,open(DB,"w",encoding="utf8"),ensure_ascii=False,indent=2)
def admin(i): return i.user.guild_permissions.administrator
def eid(): return secrets.token_hex(4).upper()

class BuyView(discord.ui.View):
    def __init__(self,pid): super().__init__(timeout=None); self.pid=pid
    @discord.ui.button(label="Comprar",emoji="🛒",style=discord.ButtonStyle.success,custom_id="ks_buy")
    async def buy(self,i,b):
        d=load(); p=next((x for x in d["products"] if x["id"]==self.pid),None)
        if not p or not p["stock"]: return await i.response.send_message("❌ Produto sem estoque.",ephemeral=True)
        cat=discord.utils.get(i.guild.categories,name="🛒 COMPRAS") or await i.guild.create_category("🛒 COMPRAS")
        ow={i.guild.default_role:discord.PermissionOverwrite(view_channel=False),i.user:discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True)}
        ch=await i.guild.create_text_channel(f"pedido-{i.user.name}",category=cat,overwrites=ow)
        oid=eid(); d["orders"].append({"id":oid,"user":i.user.id,"product":p["id"],"channel":ch.id,"status":"aguardando"}); save(d)
        e=discord.Embed(title="🛒 Pedido criado",description=f"**{p['name']}**\n💰 **R$ {p['price']:.2f}**\n\nPedido: `{oid}`",color=0x7c3aed)
        await ch.send(i.user.mention,embed=e,view=OrderView(oid))
        await i.response.send_message(f"✅ Pedido aberto: {ch.mention}",ephemeral=True)

class OrderView(discord.ui.View):
    def __init__(self,oid): super().__init__(timeout=None); self.oid=oid
    @discord.ui.button(label="Confirmar pagamento",emoji="✅",style=discord.ButtonStyle.success)
    async def confirm(self,i,b):
        if not admin(i): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
        d=load(); o=next((x for x in d["orders"] if x["id"]==self.oid),None)
        p=next((x for x in d["products"] if x["id"]==o["product"]),None) if o else None
        if not p or not p["stock"]: return await i.response.send_message("❌ Estoque vazio.",ephemeral=True)
        item=p["stock"].pop(0); o["status"]="entregue"; save(d)
        m=i.guild.get_member(o["user"])
        if m:
            try: await m.send(f"📦 **Entrega do pedido {self.oid}**\n\n`{item}`")
            except discord.Forbidden: pass
        await i.response.send_message("✅ Pedido entregue por DM.")
    @discord.ui.button(label="Fechar",emoji="🔒",style=discord.ButtonStyle.danger)
    async def close(self,i,b):
        if not admin(i): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
        await i.channel.delete()

class SetupModal(discord.ui.Modal,title="Configuração da King Store"):
    channel_name=discord.ui.TextInput(label="Nome do canal da loja",default="🛍️・loja",max_length=90)
    async def on_submit(self,i):
        d=load(); d["settings"][str(i.guild.id)]={"store_channel":i.channel.id,"name":str(self.channel_name)}; save(d)
        await i.response.send_message("✅ Loja configurada neste canal. Agora use `/produto criar` e depois `/painel`.",ephemeral=True)

class Bot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!",intents=discord.Intents.all(),help_command=None)
    async def setup_hook(self):
        self.add_view(BuyView("persistent"))
        await self.tree.sync()

bot=Bot()

@bot.event
async def on_ready(): print("King Store V2 online:",bot.user)

@bot.tree.command(name="setup",description="Configura a loja sem editar código")
async def setup(i):
    if not admin(i): return await i.response.send_message("❌ Apenas administradores.",ephemeral=True)
    await i.response.send_modal(SetupModal())

produto=app_commands.Group(name="produto",description="Gerenciar produtos")
@produto.command(name="criar",description="Criar produto")
async def criar(i,nome:str,preco:float,descricao:str=""):
    if not admin(i): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    d=load(); p={"id":eid(),"name":nome,"price":preco,"description":descricao,"stock":[]}
    d["products"].append(p); save(d); await i.response.send_message(f"✅ Produto criado: `{p['id']}`",ephemeral=True)
@produto.command(name="estoque",description="Adicionar item/Key")
async def estoque(i,id:str,item:str):
    if not admin(i): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    d=load(); p=next((x for x in d["products"] if x["id"]==id.upper()),None)
    if not p:return await i.response.send_message("❌ Produto não encontrado.",ephemeral=True)
    p["stock"].append(item); save(d); await i.response.send_message("✅ Adicionado ao estoque.",ephemeral=True)
@produto.command(name="listar",description="Listar produtos")
async def listar(i):
    d=load(); await i.response.send_message("\n".join(f"`{p['id']}` • **{p['name']}** • R$ {p['price']:.2f} • {len(p['stock'])} em estoque" for p in d["products"]) or "Nenhum produto.")
bot.tree.add_command(produto)

@bot.tree.command(name="painel",description="Publicar o catálogo")
async def painel(i):
    if not admin(i): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    d=load()
    for p in d["products"]:
        e=discord.Embed(title="🛍️ "+p["name"],description=p["description"] or "Produto digital",color=0x7c3aed)
        e.add_field(name="💰 Preço",value=f"R$ {p['price']:.2f}"); e.add_field(name="📦 Estoque",value=str(len(p["stock"])))
        await i.channel.send(embed=e,view=BuyView(p["id"]))
    await i.response.send_message("✅ Painel publicado.",ephemeral=True)

@bot.tree.command(name="pedidos",description="Ver pedidos")
async def pedidos(i):
    if not admin(i): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    d=load(); x=d["orders"][-20:]
    await i.response.send_message("\n".join(f"`{o['id']}` • <@{o['user']}> • {o['status']}" for o in x) or "Nenhum pedido.",ephemeral=True)

@bot.tree.command(name="gerarkey",description="Gera uma Key aleatória para estoque")
async def gerarkey(i):
    if not admin(i): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    k="KS-"+"-".join("".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5)) for _ in range(3))
    await i.response.send_message(f"🔑 `{k}`",ephemeral=True)

if __name__=="__main__":
    if not TOKEN: raise RuntimeError("Configure DISCORD_TOKEN")
    bot.run(TOKEN)
