import discord
from discord import app_commands
from discord.ext import tasks
import datetime
import asyncio
from config import *

spam_tracker  = {}  # {guild_id: {user_id: [timestamps]}}
streak_data   = {}  # {guild_id: {user_id: {last_seen, streak}}}
missions_data = {}  # {guild_id: {user_id: {date, tasks_done}}}

DAILY_MISSIONS = [
    {"id": "msg10",   "desc": "📝 Envie 10 mensagens",           "req": 10,  "type": "messages", "xp": 50},
    {"id": "msg25",   "desc": "📝 Envie 25 mensagens",           "req": 25,  "type": "messages", "xp": 100},
    {"id": "react5",  "desc": "❤️ Reaja a 5 mensagens",          "req": 5,   "type": "reactions","xp": 30},
]


def get_streak(gid, uid):
    return streak_data.get(str(gid), {}).get(str(uid), {"last_seen": None, "streak": 0})

def set_streak(gid, uid, data):
    g, u = str(gid), str(uid)
    if g not in streak_data: streak_data[g] = {}
    streak_data[g][u] = data

def update_streak(gid, uid):
    """Atualiza streak diário. Retorna (streak_atual, is_new_day)."""
    data  = get_streak(gid, uid)
    today = datetime.date.today().isoformat()
    if data["last_seen"] == today:
        return data["streak"], False
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    if data["last_seen"] == yesterday:
        data["streak"] += 1
    else:
        data["streak"] = 1
    data["last_seen"] = today
    set_streak(gid, uid, data)
    return data["streak"], True


def setup_commands(tree: app_commands.CommandTree, bot):

    # ── Evento de mensagem (XP + streak + anti-spam) ──
    @bot.event
    async def on_message(message):
        if message.author.bot or not message.guild: return

        gid = message.guild.id
        uid = message.author.id
        now = datetime.datetime.utcnow().timestamp()

        # Anti-spam
        key = f"{gid}:{uid}"
        if key not in spam_tracker: spam_tracker[key] = []
        spam_tracker[key] = [t for t in spam_tracker[key] if now - t < SPAM_SECONDS]
        spam_tracker[key].append(now)
        if len(spam_tracker[key]) >= SPAM_LIMIT:
            try:
                until = discord.utils.utcnow() + datetime.timedelta(minutes=5)
                await message.author.timeout(until, reason="Auto-mute: spam detectado")
                await message.channel.send(
                    f"⚠️ {message.author.mention} foi silenciado por **5 minutos** por spam.",
                    delete_after=10
                )
                spam_tracker[key] = []
            except: pass
            return

        # Anti-link (só permite links para Leitor+)
        leitor_role = discord.utils.get(message.guild.roles, name="📖 Leitor")
        if leitor_role and leitor_role not in message.author.roles:
            if "http://" in message.content or "https://" in message.content:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"🔗 {message.author.mention} você precisa ser **Leitor** para enviar links!",
                        delete_after=5
                    )
                except: pass
                return

        # XP
        data = get_xp(gid, uid)
        data["xp"]       = data.get("xp", 0) + XP_PER_MESSAGE
        data["messages"] = data.get("messages", 0) + 1
        data["total_xp"] = data.get("total_xp", 0) + XP_PER_MESSAGE
        data["level"]    = data.get("level", 1)

        # Streak
        streak, is_new_day = update_streak(gid, uid)
        if is_new_day and streak > 1:
            bonus = streak * 10
            data["xp"]       += bonus
            data["total_xp"] += bonus

        # Level up
        if data["xp"] >= xp_needed(data["level"]):
            data["level"] += 1
            data["xp"]     = 0
            set_xp(gid, uid, data)
            await handle_level_up(message.guild, message.author, data["level"], streak)
        else:
            set_xp(gid, uid, data)

        # Missões
        await check_missions(message.guild, message.author, "messages")

        await bot.process_commands(message)


    async def handle_level_up(guild, member, level, streak):
        ch = discord.utils.get(guild.channels, name=CONQUEST_CHANNEL)
        if ch:
            streak_txt = f" | 🔥 Streak: {streak} dias!" if streak > 1 else ""
            embed = discord.Embed(
                title="🎉 Subiu de Nível!",
                description=f"{member.mention} chegou ao **nível {level}**! 🚀{streak_txt}",
                color=0xFF6B9D
            )
            await ch.send(embed=embed)
        if level in LEVEL_ROLES:
            role = discord.utils.get(guild.roles, name=LEVEL_ROLES[level])
            if role and role not in member.roles:
                await member.add_roles(role)


    async def check_missions(guild, member, action_type):
        gid   = str(guild.id)
        uid   = str(member.id)
        today = datetime.date.today().isoformat()
        if gid not in missions_data: missions_data[gid] = {}
        if uid not in missions_data[gid]: missions_data[gid][uid] = {"date": today, "done": []}
        if missions_data[gid][uid]["date"] != today:
            missions_data[gid][uid] = {"date": today, "done": []}

        data = get_xp(gid, uid)
        for m in DAILY_MISSIONS:
            if m["id"] in missions_data[gid][uid]["done"]: continue
            if m["type"] != action_type: continue
            val = data.get("messages", 0) if action_type == "messages" else 0
            if val >= m["req"]:
                missions_data[gid][uid]["done"].append(m["id"])
                data["xp"]       = data.get("xp", 0) + m["xp"]
                data["total_xp"] = data.get("total_xp", 0) + m["xp"]
                set_xp(gid, uid, data)
                ch = discord.utils.get(guild.channels, name=CONQUEST_CHANNEL)
                if ch:
                    await ch.send(embed=discord.Embed(
                        description=f"✅ {member.mention} completou a missão **{m['desc']}** e ganhou **+{m['xp']} XP**!",
                        color=0xFF6B9D
                    ))


    @tree.command(name="rank", description="📊 Seu nível e XP")
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def rank(interaction: discord.Interaction):
        data   = get_xp(interaction.guild.id, interaction.user.id)
        level  = data.get("level", 1)
        xp     = data.get("xp", 0)
        needed = xp_needed(level)
        filled = int((xp / needed) * 20)
        bar    = "█" * filled + "░" * (20 - filled)
        streak = get_streak(interaction.guild.id, interaction.user.id)["streak"]

        embed = discord.Embed(
            title=f"📊 Rank de {interaction.user.display_name}",
            description=(
                f"**Nível:** {level}\n"
                f"**XP:** {xp}/{needed}\n"
                f"`{bar}` {int((xp/needed)*100)}%\n"
                f"**Total XP:** {data.get('total_xp',0)}\n"
                f"**Mensagens:** {data.get('messages',0)}\n"
                f"**🔥 Streak:** {streak} dias"
            ),
            color=0xFF6B9D
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)


    @tree.command(name="top", description="🏆 Top membros mais ativos")
    async def top(interaction: discord.Interaction):
        users = sorted(
            xp_data.get(str(interaction.guild.id), {}).items(),
            key=lambda x: (x[1].get("level",1), x[1].get("xp",0)),
            reverse=True
        )[:10]
        medals = ["🥇","🥈","🥉"] + ["🏅"] * 7
        lines  = []
        for n, (uid, d) in enumerate(users):
            m = interaction.guild.get_member(int(uid))
            name = m.display_name if m else f"ID {uid}"
            lines.append(f"{medals[n]} **{name}** — Nível {d.get('level',1)} ({d.get('messages',0)} msgs)")
        await interaction.response.send_message(embed=discord.Embed(
            title="🏆 Top 10 Membros",
            description="\n".join(lines) or "Sem dados ainda.",
            color=0xFF6B9D
        ))


    @tree.command(name="missoes", description="📋 Veja suas missões diárias")
    async def missoes(interaction: discord.Interaction):
        gid   = str(interaction.guild.id)
        uid   = str(interaction.user.id)
        today = datetime.date.today().isoformat()
        done  = missions_data.get(gid, {}).get(uid, {}).get("done", []) if missions_data.get(gid, {}).get(uid, {}).get("date") == today else []
        data  = get_xp(gid, uid)

        lines = []
        for m in DAILY_MISSIONS:
            status = "✅" if m["id"] in done else "⏳"
            prog   = data.get("messages", 0) if m["type"] == "messages" else 0
            lines.append(f"{status} {m['desc']} — `{min(prog, m['req'])}/{m['req']}` (+{m['xp']} XP)")

        embed = discord.Embed(
            title=f"📋 Missões Diárias de {interaction.user.display_name}",
            description="\n".join(lines),
            color=0xFF6B9D
        )
        embed.set_footer(text="Missões reiniciam à meia-noite!")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @tree.command(name="streak", description="🔥 Veja seu streak de presença")
    async def streak_cmd(interaction: discord.Interaction):
        s = get_streak(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(embed=discord.Embed(
            description=f"🔥 Seu streak atual: **{s['streak']} dias consecutivos**!\nÚltimo acesso: {s['last_seen'] or 'Nunca'}",
            color=0xFF6B9D
        ), ephemeral=True)


    @tree.command(name="loja", description="🛒 Loja de cargos com XP")
    async def loja(interaction: discord.Interaction):
        data  = get_xp(interaction.guild.id, interaction.user.id)
        total = data.get("total_xp", 0)
        lines = [f"**{name}** — `{info['price']} XP`" for name, info in shop_items.items()]
        embed = discord.Embed(
            title="🛒 Loja de Cargos",
            description="\n".join(lines) + f"\n\n💰 Seu XP total: **{total}**\nUse `/comprar [nome]` para adquirir!",
            color=0xFF6B9D
        )
        await interaction.response.send_message(embed=embed)


    @tree.command(name="comprar", description="💳 Compra um cargo da loja")
    async def comprar(interaction: discord.Interaction, item: str):
        if item not in shop_items:
            await interaction.response.send_message("❌ Item não encontrado. Use `/loja` para ver os itens.", ephemeral=True)
            return
        info  = shop_items[item]
        data  = get_xp(interaction.guild.id, interaction.user.id)
        total = data.get("total_xp", 0)
        if total < info["price"]:
            await interaction.response.send_message(f"❌ XP insuficiente! Você tem **{total}** e precisa de **{info['price']}**.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name=info["role"])
        if not role:
            await interaction.response.send_message("❌ Cargo não encontrado no servidor.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("✅ Você já tem este cargo!", ephemeral=True)
            return
        data["total_xp"] -= info["price"]
        set_xp(interaction.guild.id, interaction.user.id, data)
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"🎉 Você comprou **{item}** por **{info['price']} XP**!", ephemeral=True)


    @tree.command(name="darxp", description="🎁 Transfere XP para outro membro")
    async def darxp(interaction: discord.Interaction, membro: discord.Member, quantidade: int):
        if quantidade <= 0:
            await interaction.response.send_message("❌ Quantidade inválida.", ephemeral=True); return
        data_from = get_xp(interaction.guild.id, interaction.user.id)
        if data_from.get("total_xp", 0) < quantidade:
            await interaction.response.send_message("❌ XP insuficiente.", ephemeral=True); return
        data_from["total_xp"] -= quantidade
        set_xp(interaction.guild.id, interaction.user.id, data_from)
        data_to = get_xp(interaction.guild.id, membro.id)
        data_to["total_xp"] = data_to.get("total_xp", 0) + quantidade
        set_xp(interaction.guild.id, membro.id, data_to)
        await interaction.response.send_message(f"🎁 Você enviou **{quantidade} XP** para {membro.mention}!")