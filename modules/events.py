import discord
from discord import app_commands
from discord.ext import tasks
import datetime
import asyncio
import random
from config import *

giveaways      = {}
scheduled_msgs = []
_bot_instance  = None


@tasks.loop(minutes=10)
async def update_stats():
    if not _bot_instance: return
    for guild in _bot_instance.guilds:
        online = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)
        for vc in guild.voice_channels:
            try:
                if vc.name.startswith("👥 Membros:"):
                    await vc.edit(name=f"👥 Membros: {guild.member_count}")
                elif vc.name.startswith("🟢 Online:"):
                    await vc.edit(name=f"🟢 Online: {online}")
            except: pass


@tasks.loop(minutes=1)
async def check_scheduled():
    if not _bot_instance: return
    now     = datetime.datetime.utcnow()
    to_send = [m for m in scheduled_msgs if m["send_at"] <= now]
    for m in to_send:
        scheduled_msgs.remove(m)
        for guild in _bot_instance.guilds:
            ch = guild.get_channel(m["channel_id"])
            if ch:
                await ch.send(m["message"])


@tasks.loop(hours=168)
async def weekly_ranking():
    if not _bot_instance: return
    for guild in _bot_instance.guilds:
        ch = discord.utils.get(guild.channels, name=RANKING_CHANNEL)
        if not ch: continue
        from config import xp_data
        users = sorted(xp_data.get(str(guild.id),{}).items(),
                       key=lambda x: x[1].get("messages",0), reverse=True)[:10]
        if not users: continue
        medals = ["🥇","🥈","🥉"]+["🏅"]*7
        lines  = [f"{medals[i]} **{(guild.get_member(int(uid)) or type('_',(),{'display_name':f'ID {uid}'})).display_name}** — {d.get('messages',0)} msgs"
                  for i,(uid,d) in enumerate(users)]
        await ch.send(embed=discord.Embed(
            title="🏆 Ranking Semanal — Gato Comics",
            description="\n".join(lines), color=0xFF6B9D, timestamp=datetime.datetime.utcnow()
        ))


def start_tasks(bot):
    """Chame esta função no on_ready do bot."""
    global _bot_instance
    _bot_instance = bot
    if not update_stats.is_running():    update_stats.start()
    if not check_scheduled.is_running(): check_scheduled.start()
    if not weekly_ranking.is_running():  weekly_ranking.start()


def setup_commands(tree: app_commands.CommandTree, bot):

    # ── SORTEIO ───────────────────────────────────────────────

    class GiveawayView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="🎉 Participar", style=discord.ButtonStyle.success, custom_id="giveaway_join")
        async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
            g = giveaways.get(interaction.message.id)
            if not g:
                await interaction.response.send_message("❌ Sorteio não encontrado.", ephemeral=True); return
            if g.get("role_req"):
                role = interaction.guild.get_role(g["role_req"])
                if role and role not in interaction.user.roles:
                    await interaction.response.send_message(f"❌ Você precisa do cargo {role.mention}.", ephemeral=True); return
            if interaction.user.id in g["participants"]:
                await interaction.response.send_message("✅ Você já está participando!", ephemeral=True); return
            g["participants"].append(interaction.user.id)
            await interaction.response.send_message(f"🎉 Participando! ({len(g['participants'])} inscritos)", ephemeral=True)

    bot.add_view(GiveawayView())

    @tree.command(name="sorteio", description="🎁 Cria um sorteio")
    @staff_only()
    @channel_only(GIVEAWAY_CHANNEL)
    @app_commands.checks.cooldown(1, 3600, key=lambda i: i.guild.id)
    async def sorteio(interaction: discord.Interaction, premio: str, minutos: int = 60, cargo: discord.Role = None):
        end = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutos)
        embed = discord.Embed(
            title="🎁 SORTEIO!", color=0xFF6B9D, timestamp=end,
            description=(
                f"**Prêmio:** {premio}\n"
                f"**Término:** <t:{int(end.timestamp())}:R>\n"
                f"**Requisito:** {cargo.mention if cargo else 'Todos'}\n\n"
                "Clique em 🎉 para participar!"
            )
        )
        embed.set_footer(text="Sorteio encerra em")
        await interaction.response.send_message(embed=embed, view=GiveawayView())
        msg = await interaction.original_response()
        giveaways[msg.id] = {"channel_id": interaction.channel.id, "prize": premio,
                              "role_req": cargo.id if cargo else None, "participants": []}

        async def end_giveaway():
            await asyncio.sleep(minutos * 60)
            g = giveaways.pop(msg.id, None)
            if not g or not g["participants"]:
                await interaction.channel.send("😢 Ninguém participou do sorteio."); return
            winner = interaction.guild.get_member(random.choice(g["participants"]))
            await interaction.channel.send(embed=discord.Embed(
                title="🎉 Resultado do Sorteio!",
                description=f"**Prêmio:** {premio}\n**Vencedor:** {winner.mention if winner else '?'} 🏆",
                color=discord.Color.gold()
            ))
        asyncio.create_task(end_giveaway())



    # ── ENQUETE ───────────────────────────────────────────────

    @tree.command(name="enquete", description="📊 Cria uma enquete")
    @staff_only()
    @channel_only(POLL_CHANNEL)
    @app_commands.checks.cooldown(1, 1800, key=lambda i: i.guild.id)
    async def enquete(interaction: discord.Interaction, pergunta: str, opcao1: str, opcao2: str, opcao3: str = None, opcao4: str = None):
        opcoes = [o for o in [opcao1, opcao2, opcao3, opcao4] if o]
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣"]
        desc   = "\n".join([f"{emojis[i]} {o}" for i, o in enumerate(opcoes)])
        embed  = discord.Embed(title=f"📊 {pergunta}", description=desc, color=0xFF6B9D)
        embed.set_footer(text="Reaja para votar!")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(opcoes)): await msg.add_reaction(emojis[i])


    # ── ANÚNCIOS ──────────────────────────────────────────────

    @tree.command(name="anunciar", description="📣 Posta um anúncio oficial")
    @staff_only()
    async def anunciar(interaction: discord.Interaction, titulo: str, descricao: str, mencionar_todos: bool = False):
        ch = discord.utils.get(interaction.guild.channels, name=ANNOUNCE_CHANNEL)
        if not ch:
            await interaction.response.send_message("❌ Canal de anúncios não encontrado.", ephemeral=True); return
        embed = discord.Embed(title=f"📣 {titulo}", description=descricao, color=0xFF6B9D, timestamp=datetime.datetime.utcnow())
        embed.set_footer(text="Gato Comics • Anúncio Oficial 🐱")
        await ch.send(content="@everyone" if mencionar_todos else "", embed=embed)
        await interaction.response.send_message("✅ Anúncio postado!", ephemeral=True)


    @tree.command(name="lancamento", description="🚀 Anuncia novo webtoon ou episódio")
    @staff_only()
    async def lancamento(interaction: discord.Interaction, titulo: str, descricao: str, link: str, genero: str = None):
        ch = discord.utils.get(interaction.guild.channels, name=LAUNCH_CHANNEL)
        if not ch:
            await interaction.response.send_message("❌ Canal não encontrado.", ephemeral=True); return
        embed = discord.Embed(
            title=f"🚀 Novo Lançamento: {titulo}",
            description=f"{descricao}\n\n🔗 [Leia agora!]({link})",
            color=0xFF6B9D, timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Gato Comics 🐱")
        genero_map = {"ação":"⚔️ Fã de Ação","romance":"💕 Fã de Romance","terror":"👻 Fã de Terror","comédia":"😂 Fã de Comédia"}
        role = discord.utils.get(interaction.guild.roles, name=genero_map.get((genero or "").lower(), ""))
        await ch.send(content=role.mention if role else "", embed=embed)
        await interaction.response.send_message("✅ Lançamento anunciado!", ephemeral=True)


    @tree.command(name="agendar", description="📅 Agenda uma mensagem para um canal")
    @staff_only()
    async def agendar(interaction: discord.Interaction, canal: discord.TextChannel, mensagem: str, minutos: int = 60):
        scheduled_msgs.append({"channel_id": canal.id, "message": mensagem, "send_at": datetime.datetime.utcnow() + datetime.timedelta(minutes=minutos)})
        await interaction.response.send_message(f"✅ Mensagem agendada para {canal.mention} em **{minutos} minutos**!", ephemeral=True)


    # Tasks registradas no bot para iniciar no on_ready
    bot._bot_ref = bot