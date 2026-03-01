import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import datetime
import random
import aiohttp
import yt_dlp

# ─────────────────────────────────────────
#  CONFIGURAÇÕES — edite aqui
# ─────────────────────────────────────────
TOKEN = "SEU_TOKEN_AQUI"

SUPPORT_ROLE_NAMES  = ["👑 Owner", "⚙️ Admin", "🛡️ Moderador"]
TICKET_CATEGORY     = "🎫 TICKETS"
TICKET_LOG_CHANNEL  = "📋・log-tickets"
MUSIC_CHANNEL_NAME  = "🎵・comandos-musica"
XP_PER_MESSAGE      = 15
WARNS_MUTE          = 3
WARNS_BAN           = 5
# ─────────────────────────────────────────

intents = discord.Intents.all()
bot     = commands.Bot(command_prefix="g!", intents=intents)
tree    = bot.tree

# Dados em memória
xp_data    = {}  # {guild_id: {user_id: {xp, level, messages}}}
warns_data = {}  # {guild_id: {user_id: [{reason, by, at}]}}
giveaways  = {}  # {message_id: {channel_id, prize, end_time, role_req, participants}}

# ══════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════

def get_xp(gid, uid):
    return xp_data.get(str(gid), {}).get(str(uid), {"xp": 0, "level": 1, "messages": 0})

def set_xp(gid, uid, data):
    g = str(gid); u = str(uid)
    if g not in xp_data: xp_data[g] = {}
    xp_data[g][u] = data

def xp_needed(level): return 100 * (level ** 2)

def get_warns(gid, uid):
    return warns_data.get(str(gid), {}).get(str(uid), [])

def add_warn(gid, uid, reason, by):
    g = str(gid); u = str(uid)
    if g not in warns_data: warns_data[g] = {}
    if u not in warns_data[g]: warns_data[g][u] = []
    warns_data[g][u].append({"reason": reason, "by": str(by), "at": datetime.datetime.utcnow().isoformat()})
    return len(warns_data[g][u])

LEVEL_ROLES = {5: "📖 Leitor", 15: "💎 Leitor VIP", 30: "⭐ Veterano"}

# ══════════════════════════════════════════
#  SETUP COMPLETO
# ══════════════════════════════════════════

@tree.command(name="setup", description="⚙️ Configura o servidor completo da Gato Comics")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    logs  = []

    await interaction.followup.send("⏳ Iniciando setup completo...", ephemeral=True)

    # ── Cargos ──
    roles_cfg = [
        {"name": "👑 Owner",             "color": discord.Color.gold(),                  "hoist": True},
        {"name": "⚙️ Admin",             "color": discord.Color.red(),                   "hoist": True},
        {"name": "🛡️ Moderador",         "color": discord.Color.blue(),                  "hoist": True},
        {"name": "🎨 Criador Parceiro",  "color": discord.Color.purple(),                "hoist": True},
        {"name": "✍️ Escritor Parceiro", "color": discord.Color.green(),                 "hoist": True},
        {"name": "⭐ Veterano",          "color": discord.Color.orange(),                "hoist": True},
        {"name": "💎 Leitor VIP",        "color": discord.Color.from_rgb(255,105,180),   "hoist": True},
        {"name": "📖 Leitor",            "color": discord.Color.light_grey(),             "hoist": False},
        {"name": "🆕 Novato",            "color": discord.Color.default(),               "hoist": False},
        {"name": "⚔️ Fã de Ação",        "color": discord.Color.from_rgb(220,50,50),     "hoist": False},
        {"name": "💕 Fã de Romance",     "color": discord.Color.from_rgb(255,150,180),   "hoist": False},
        {"name": "👻 Fã de Terror",      "color": discord.Color.from_rgb(100,60,120),    "hoist": False},
        {"name": "😂 Fã de Comédia",     "color": discord.Color.from_rgb(255,210,50),    "hoist": False},
    ]
    existing_roles = {r.name: r for r in guild.roles}
    cr = {}
    for rc in roles_cfg:
        if rc["name"] not in existing_roles:
            r = await guild.create_role(name=rc["name"], color=rc["color"], hoist=rc["hoist"], reason="Setup Gato Comics")
            cr[rc["name"]] = r
            logs.append(f"Cargo: {rc['name']}")
        else:
            cr[rc["name"]] = existing_roles[rc["name"]]

    novato = cr["🆕 Novato"]; leitor = cr["📖 Leitor"]
    mod = cr["🛡️ Moderador"]; admin = cr["⚙️ Admin"]; owner = cr["👑 Owner"]

    await guild.default_role.edit(permissions=discord.Permissions(view_channel=False))

    def ow_default():
        return {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            novato: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            leitor: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            mod:    discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True),
            admin:  discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
            owner:  discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

    def ow_readonly():
        d = ow_default()
        d[novato] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        d[leitor] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        return d

    def ow_staff():
        return {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            mod:   discord.PermissionOverwrite(view_channel=True, send_messages=True),
            admin: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            owner: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

    # ── Estrutura de canais ──
    structure = [
        ("📌 INÍCIO", [
            ("📋・regras",       "text",  "Leia antes de participar.",         ow_readonly()),
            ("📣・anúncios",      "text",  "Novidades oficiais da Gato Comics.", ow_readonly()),
            ("🎉・boas-vindas",   "text",  "Boas-vindas automáticas.",          ow_readonly()),
            ("🎭・apresentações", "text",  "Se apresente para a comunidade!",   ow_default()),
        ]),
        ("📖 WEBTOONS", [
            ("🚀・lançamentos",     "text", "Novos episódios e títulos.",       ow_readonly()),
            ("💬・discussão-geral", "text", "Papo geral sobre webtoons.",       ow_default()),
            ("⭐・recomendações",   "text", "Indique seus webtoons favoritos!", ow_default()),
            ("🔍・spoilers",        "text", "Discussão com spoilers. Cuidado!", ow_default()),
        ]),
        ("🎨 CRIADORES", [
            ("🖼️・portfólio",         "text", "Mostre seus trabalhos.",         ow_default()),
            ("🛠️・tutoriais-e-dicas",  "text", "Dicas de criação de webtoons.", ow_default()),
            ("🤝・oportunidades",      "text", "Vagas e parcerias oficiais.",    ow_readonly()),
        ]),
        ("💬 COMUNIDADE", [
            ("🗨️・bate-papo",          "text",  "Conversa geral.",          ow_default()),
            ("😂・memes-e-cultura-pop", "text",  "Memes e trends.",          ow_default()),
            ("🎮・off-topic",           "text",  "Qualquer assunto aqui!",   ow_default()),
            ("📊・enquetes",            "text",  "Enquetes da comunidade.",  ow_default()),
            ("🎁・sorteios",            "text",  "Sorteios oficiais.",       ow_default()),
        ]),
        ("🎵 VOZ & MÚSICA", [
            ("🎵・comandos-musica", "text",  "Use comandos de música aqui.", ow_default()),
            ("🔊 Sala Geral",       "voice", "",                             ow_default()),
            ("📚 Clube de Leitura", "voice", "",                             ow_default()),
            ("🎮 Gaming",           "voice", "",                             ow_default()),
            ("🎵 Música",           "voice", "",                             ow_default()),
        ]),
        ("🏆 RANKING", [
            ("🏆・ranking",    "text", "Top membros mais ativos.",       ow_readonly()),
            ("⭐・conquistas", "text", "Conquistas e subidas de nível.", ow_readonly()),
        ]),
        ("🎫 SUPORTE", [
            ("🎫・abrir-ticket", "text", "Clique para abrir um ticket.", ow_readonly()),
            ("📋・log-tickets",  "text", "Log de tickets fechados.",     ow_staff()),
        ]),
    ]

    ticket_ch = rules_ch = updates_ch = None

    for cat_name, channels in structure:
        cat = discord.utils.get(guild.categories, name=cat_name) or await guild.create_category(cat_name, overwrites=ow_default())
        for ch_name, ch_type, topic, overwrites in channels:
            existing = discord.utils.get(guild.channels, name=ch_name)
            if existing:
                ch = existing
            elif ch_type == "text":
                ch = await guild.create_text_channel(ch_name, category=cat, topic=topic, overwrites=overwrites)
                logs.append(f"Canal: {ch_name}")
            else:
                ch = await guild.create_voice_channel(ch_name, category=cat, overwrites=overwrites)
                logs.append(f"Voz: {ch_name}")

            if ch_name == "🎫・abrir-ticket": ticket_ch  = ch
            if ch_name == "📋・regras":       rules_ch   = ch
            if ch_name == "📣・anúncios":     updates_ch = ch

    # ── Habilitar Comunidade ──
    try:
        await guild.edit(
            community=True,
            rules_channel=rules_ch,
            public_updates_channel=updates_ch,
            verification_level=discord.VerificationLevel.low,
            explicit_content_filter=discord.ContentFilter.all_members,
        )
        logs.append("Modo Comunidade habilitado!")
    except Exception as e:
        logs.append(f"Comunidade (configure manualmente): {e}")

    # ── Onboarding via API ──
    try:
        onboarding = {
            "prompts": [
                {
                    "id": "1", "type": 1, "title": "Você é...?",
                    "single_select": True, "required": True, "in_onboarding": True,
                    "options": [
                        {"id": "101", "title": "📖 Leitor de Webtoons",    "role_ids": [str(leitor.id)]},
                        {"id": "102", "title": "🎨 Artista / Criador",     "role_ids": [str(cr["🎨 Criador Parceiro"].id)]},
                        {"id": "103", "title": "✍️ Escritor / Roteirista", "role_ids": [str(cr["✍️ Escritor Parceiro"].id)]},
                        {"id": "104", "title": "👀 Só explorando",         "role_ids": [str(novato.id)]},
                    ]
                },
                {
                    "id": "2", "type": 1, "title": "Quais gêneros te interessam?",
                    "single_select": False, "required": False, "in_onboarding": True,
                    "options": [
                        {"id": "201", "title": "⚔️ Ação",    "role_ids": [str(cr["⚔️ Fã de Ação"].id)]},
                        {"id": "202", "title": "💕 Romance",  "role_ids": [str(cr["💕 Fã de Romance"].id)]},
                        {"id": "203", "title": "👻 Terror",   "role_ids": [str(cr["👻 Fã de Terror"].id)]},
                        {"id": "204", "title": "😂 Comédia",  "role_ids": [str(cr["😂 Fã de Comédia"].id)]},
                    ]
                },
                {
                    "id": "3", "type": 1, "title": "Como nos encontrou?",
                    "single_select": True, "required": False, "in_onboarding": True,
                    "options": [
                        {"id": "301", "title": "📱 Instagram / TikTok", "role_ids": []},
                        {"id": "302", "title": "🔍 Google",              "role_ids": []},
                        {"id": "303", "title": "👥 Indicação de amigo",  "role_ids": []},
                        {"id": "304", "title": "🌐 Outro",               "role_ids": []},
                    ]
                },
            ],
            "default_channel_ids": [str(rules_ch.id), str(updates_ch.id)],
            "enabled": True,
            "mode": 1
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"https://discord.com/api/v10/guilds/{guild.id}/onboarding",
                headers={"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"},
                json=onboarding
            ) as resp:
                logs.append("Onboarding configurado!" if resp.status == 200 else f"Onboarding erro {resp.status}")
    except Exception as e:
        logs.append(f"Onboarding: {e}")

    # ── Boas-vindas e painel de ticket ──
    welcome_ch = discord.utils.get(guild.channels, name="🎉・boas-vindas")
    if welcome_ch:
        embed = discord.Embed(
            title="🐱 Bem-vindo à Gato Comics!",
            description=(
                "Olá! Você chegou na comunidade oficial da **Gato Comics** 🇧🇷\n"
                "A editora digital de webtoons 100% brasileira!\n\n"
                f"📋 Leia as {rules_ch.mention}\n"
                "🎭 Se apresente no canal de apresentações!\n"
                "📖 Explore webtoons e participe das discussões."
            ),
            color=0xFF6B9D
        )
        embed.set_footer(text="Gato Comics • A sua editora de webtoons 🐱")
        await welcome_ch.send(embed=embed)

    if ticket_ch:
        await send_ticket_panel(ticket_ch)

    embed_done = discord.Embed(
        title="✅ Setup concluído!",
        description="\n".join([f"✅ {l}" for l in logs[-20:]]),
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )
    await interaction.followup.send(embed=embed_done, ephemeral=True)


# ══════════════════════════════════════════
#  TICKETS
# ══════════════════════════════════════════

async def send_ticket_panel(channel):
    embed = discord.Embed(
        title="🎫 Central de Suporte — Gato Comics",
        description="Selecione a categoria do seu problema abaixo.\nUm canal privado será aberto para você e nossa equipe. 🐱",
        color=0xFF6B9D
    )
    embed.set_footer(text="Apenas você e a equipe verão seu ticket.")
    await channel.send(embed=embed, view=TicketCategoryView())


class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o tipo de suporte...",
            custom_id="ticket_category",
            options=[
                discord.SelectOption(label="Problema de Leitura", emoji="📖", value="leitura",  description="Erro ao ler um webtoon"),
                discord.SelectOption(label="Dúvida sobre Obra",   emoji="📚", value="obra",     description="Perguntas sobre algum título"),
                discord.SelectOption(label="Pagamento",           emoji="💳", value="pagamento",description="Problema com assinatura ou compra"),
                discord.SelectOption(label="Bug Técnico",         emoji="🐛", value="bug",      description="Erro técnico na plataforma"),
                discord.SelectOption(label="Quero ser Parceiro",  emoji="🤝", value="parceria", description="Interesse em publicar na Gato Comics"),
                discord.SelectOption(label="Outros",              emoji="❓", value="outros",   description="Qualquer outro assunto"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        cat_map = {
            "leitura":  ("📖 Leitura",   "Descreva qual webtoon e qual o problema ao ler."),
            "obra":     ("📚 Obra",      "Qual o título da obra e sua dúvida?"),
            "pagamento":("💳 Pagamento", "Descreva o problema com pagamento ou assinatura."),
            "bug":      ("🐛 Bug",       "Descreva o erro (dispositivo, versão, etc)."),
            "parceria": ("🤝 Parceria",  "Conte sobre você e seu projeto!"),
            "outros":   ("❓ Outros",    "Descreva sua dúvida ou solicitação."),
        }
        cat_name, first_msg = cat_map[self.values[0]]
        guild = interaction.guild
        user  = interaction.user
        slug  = user.name.lower().replace(' ', '-')[:20]
        ticket_name = f"ticket-{slug}"

        existing = discord.utils.get(guild.channels, name=ticket_name)
        if existing:
            await interaction.response.send_message(f"❌ Você já tem um ticket: {existing.mention}", ephemeral=True)
            return

        cat = discord.utils.get(guild.categories, name=TICKET_CATEGORY) or await guild.create_category(TICKET_CATEGORY)
        support = [r for r in guild.roles if r.name in SUPPORT_ROLE_NAMES]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        }
        for r in support:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

        ch = await guild.create_text_channel(ticket_name, category=cat, overwrites=overwrites,
            topic=f"{cat_name} | {user.name} | {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")

        embed = discord.Embed(
            title=f"🎫 Ticket — {cat_name}",
            description=f"Olá {user.mention}! 👋\n\n**{first_msg}**\n\nNossa equipe responderá em breve.\nQuando resolvido, clique em **🔒 Fechar Ticket**.",
            color=0xFF6B9D, timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Gato Comics Support 🐱")
        mentions = " ".join(r.mention for r in support)
        await ch.send(content=f"{user.mention} {mentions}", embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"✅ Ticket aberto: {ch.mention}", ephemeral=True)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch    = interaction.channel
        guild = interaction.guild
        support = [r for r in interaction.user.roles if r.name in SUPPORT_ROLE_NAMES]
        is_owner = ch.name.endswith(interaction.user.name.lower().replace(' ', '-')[:20])
        if not support and not is_owner:
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Fechando em 5 segundos...")
        log_ch = discord.utils.get(guild.channels, name=TICKET_LOG_CHANNEL)
        if log_ch:
            msgs = [f"[{m.created_at.strftime('%d/%m %H:%M')}] {m.author.display_name}: {m.content}"
                    async for m in ch.history(limit=200, oldest_first=True) if not m.author.bot]
            embed = discord.Embed(
                title=f"📋 Ticket Fechado — #{ch.name}",
                description=f"Fechado por: {interaction.user.mention}\n\n**Log:**\n```\n" + "\n".join(msgs[-30:]) + "\n```",
                color=discord.Color.red(), timestamp=datetime.datetime.utcnow()
            )
            await log_ch.send(embed=embed)
        await asyncio.sleep(5)
        await ch.delete()


@tree.command(name="ticketpainel", description="📩 Reenvia o painel de tickets")
@app_commands.checks.has_permissions(manage_channels=True)
async def ticket_panel_cmd(interaction: discord.Interaction):
    await send_ticket_panel(interaction.channel)
    await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)


# ══════════════════════════════════════════
#  MÚSICA
# ══════════════════════════════════════════

music_queues  = {}
music_current = {}
YDL_OPTS = {'format': 'bestaudio/best', 'quiet': True, 'default_search': 'ytsearch'}
FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


async def get_audio(query):
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        if 'entries' in info: info = info['entries'][0]
        return info.get('url'), info.get('title', 'Desconhecido')


async def play_next(guild):
    vc = guild.voice_client
    if not vc: return
    gid = guild.id
    if not music_queues.get(gid):
        music_current.pop(gid, None)
        await vc.disconnect(); return
    url, title = music_queues[gid].pop(0)
    music_current[gid] = title
    vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTS),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop))


def music_only():
    async def pred(i: discord.Interaction):
        ch = discord.utils.get(i.guild.channels, name=MUSIC_CHANNEL_NAME)
        if ch and i.channel.id != ch.id:
            await i.response.send_message(f"❌ Use em {ch.mention}!", ephemeral=True)
            return False
        return True
    return app_commands.check(pred)


@tree.command(name="play", description="🎵 Toca uma música (YouTube/Spotify)")
@music_only()
async def play(interaction: discord.Interaction, musica: str):
    await interaction.response.defer()
    if not interaction.user.voice:
        await interaction.followup.send("❌ Entre em um canal de voz primeiro!", ephemeral=True); return
    vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect()
    gid = interaction.guild.id
    if gid not in music_queues: music_queues[gid] = []
    try:
        url, title = await get_audio(musica)
    except:
        await interaction.followup.send("❌ Música não encontrada.", ephemeral=True); return
    if vc.is_playing():
        music_queues[gid].append((url, title))
        await interaction.followup.send(embed=discord.Embed(description=f"📋 **{title}** adicionada à fila! (#{len(music_queues[gid])})", color=0xFF6B9D))
    else:
        music_queues[gid].insert(0, (url, title))
        await play_next(interaction.guild)
        await interaction.followup.send(embed=discord.Embed(description=f"▶️ Tocando: **{title}**", color=0xFF6B9D))

@tree.command(name="skip",       description="⏭️ Pula para a próxima")    
@music_only()
async def skip(i: discord.Interaction):
    vc = i.guild.voice_client
    if vc and vc.is_playing(): vc.stop(); await i.response.send_message("⏭️ Pulando!", ephemeral=True)
    else: await i.response.send_message("❌ Nada tocando.", ephemeral=True)

@tree.command(name="pause",      description="⏸️ Pausa a música")
@music_only()
async def pause(i: discord.Interaction):
    vc = i.guild.voice_client
    if vc and vc.is_playing(): vc.pause(); await i.response.send_message("⏸️ Pausado.", ephemeral=True)
    else: await i.response.send_message("❌ Nada tocando.", ephemeral=True)

@tree.command(name="resume",     description="▶️ Retoma a música")
@music_only()
async def resume(i: discord.Interaction):
    vc = i.guild.voice_client
    if vc and vc.is_paused(): vc.resume(); await i.response.send_message("▶️ Retomado.", ephemeral=True)
    else: await i.response.send_message("❌ Nada pausado.", ephemeral=True)

@tree.command(name="stop",       description="⏹️ Para e desconecta")
@music_only()
async def stop(i: discord.Interaction):
    gid = i.guild.id
    music_queues.pop(gid, None); music_current.pop(gid, None)
    vc = i.guild.voice_client
    if vc: await vc.disconnect()
    await i.response.send_message("⏹️ Parado.", ephemeral=True)

@tree.command(name="queue",      description="📋 Fila de músicas")
@music_only()
async def queue_cmd(i: discord.Interaction):
    gid = i.guild.id
    desc = f"▶️ **Tocando:** {music_current.get(gid,'Nenhuma')}\n\n"
    fila = music_queues.get(gid, [])
    desc += "\n".join([f"`{n+1}.` {t}" for n, (_, t) in enumerate(fila[:10])]) if fila else "*Fila vazia*"
    await i.response.send_message(embed=discord.Embed(title="🎵 Fila", description=desc, color=0xFF6B9D))

@tree.command(name="nowplaying", description="🎵 Música tocando agora")
@music_only()
async def nowplaying(i: discord.Interaction):
    cur = music_current.get(i.guild.id)
    desc = f"▶️ **{cur}**" if cur else "❌ Nada tocando."
    await i.response.send_message(embed=discord.Embed(description=desc, color=0xFF6B9D))

@tree.command(name="volume",     description="🔊 Ajusta volume (0-100)")
@music_only()
async def volume(i: discord.Interaction, valor: int):
    vc = i.guild.voice_client
    if vc and vc.source:
        vc.source = discord.PCMVolumeTransformer(vc.source, volume=max(0, min(valor,100))/100)
        await i.response.send_message(f"🔊 Volume: **{valor}%**", ephemeral=True)
    else: await i.response.send_message("❌ Nada tocando.", ephemeral=True)


# ══════════════════════════════════════════
#  XP / NÍVEIS
# ══════════════════════════════════════════

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    data = get_xp(message.guild.id, message.author.id)
    data["xp"] = data.get("xp",0) + XP_PER_MESSAGE
    data["messages"] = data.get("messages",0) + 1
    data["level"] = data.get("level",1)
    if data["xp"] >= xp_needed(data["level"]):
        data["level"] += 1; data["xp"] = 0
        set_xp(message.guild.id, message.author.id, data)
        await level_up(message.guild, message.author, data["level"])
    else:
        set_xp(message.guild.id, message.author.id, data)
    await bot.process_commands(message)


async def level_up(guild, member, level):
    ch = discord.utils.get(guild.channels, name="⭐・conquistas")
    if ch:
        await ch.send(embed=discord.Embed(
            title="🎉 Subiu de Nível!",
            description=f"{member.mention} chegou ao **nível {level}**! 🚀",
            color=0xFF6B9D))
    if level in LEVEL_ROLES:
        role = discord.utils.get(guild.roles, name=LEVEL_ROLES[level])
        if role and role not in member.roles:
            await member.add_roles(role)


@tree.command(name="rank", description="📊 Seu nível e XP")
async def rank(i: discord.Interaction):
    data   = get_xp(i.guild.id, i.user.id)
    level  = data.get("level",1); xp = data.get("xp",0)
    needed = xp_needed(level)
    filled = int((xp/needed)*20)
    bar    = "█"*filled + "░"*(20-filled)
    embed  = discord.Embed(
        title=f"📊 Rank de {i.user.display_name}",
        description=f"**Nível:** {level}\n**XP:** {xp}/{needed}\n`{bar}` {int((xp/needed)*100)}%\n**Mensagens:** {data.get('messages',0)}",
        color=0xFF6B9D)
    embed.set_thumbnail(url=i.user.display_avatar.url)
    await i.response.send_message(embed=embed)


@tree.command(name="top", description="🏆 Top membros mais ativos")
async def top(i: discord.Interaction):
    users = sorted(xp_data.get(str(i.guild.id),{}).items(),
                   key=lambda x:(x[1].get("level",1),x[1].get("xp",0)), reverse=True)[:10]
    medals = ["🥇","🥈","🥉"]+["🏅"]*7
    lines  = [f"{medals[n]} **{(i.guild.get_member(int(uid)) or type('_',(),{'display_name':f'ID {uid}'})).display_name}** — Nível {d.get('level',1)}"
              for n,(uid,d) in enumerate(users)]
    await i.response.send_message(embed=discord.Embed(
        title="🏆 Top 10 Membros", description="\n".join(lines) or "Sem dados.", color=0xFF6B9D))


# ══════════════════════════════════════════
#  MODERAÇÃO
# ══════════════════════════════════════════

@tree.command(name="kick", description="👢 Expulsa um membro")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    await membro.kick(reason=motivo)
    await i.response.send_message(f"👢 **{membro}** expulso. Motivo: {motivo}", ephemeral=True)

@tree.command(name="ban", description="🔨 Bane um membro")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    await membro.ban(reason=motivo)
    await i.response.send_message(f"🔨 **{membro}** banido. Motivo: {motivo}", ephemeral=True)

@tree.command(name="mute", description="🔇 Silencia um membro")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(i: discord.Interaction, membro: discord.Member, minutos: int = 10, motivo: str = "Sem motivo"):
    await membro.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=minutos), reason=motivo)
    await i.response.send_message(f"🔇 **{membro}** silenciado por {minutos}min.", ephemeral=True)

@tree.command(name="unmute", description="🔊 Remove silêncio")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(i: discord.Interaction, membro: discord.Member):
    await membro.timeout(None)
    await i.response.send_message(f"🔊 Silêncio removido de **{membro}**.", ephemeral=True)

@tree.command(name="clear", description="🧹 Apaga mensagens")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, quantidade: int = 10):
    await i.response.defer(ephemeral=True)
    deleted = await i.channel.purge(limit=quantidade)
    await i.followup.send(f"🧹 {len(deleted)} mensagens apagadas.", ephemeral=True)

@tree.command(name="warn", description="⚠️ Avisa um membro")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(i: discord.Interaction, membro: discord.Member, motivo: str):
    total = add_warn(i.guild.id, membro.id, motivo, i.user)
    await i.response.send_message(f"⚠️ **{membro}** recebeu aviso #{total}. Motivo: {motivo}", ephemeral=True)
    if total >= WARNS_BAN:
        await membro.ban(reason=f"Auto-ban: {total} avisos")
    elif total >= WARNS_MUTE:
        await membro.timeout(discord.utils.utcnow() + datetime.timedelta(hours=1), reason=f"Auto-mute: {total} avisos")

@tree.command(name="warnings", description="📋 Avisos de um membro")
@app_commands.checks.has_permissions(manage_messages=True)
async def warnings_cmd(i: discord.Interaction, membro: discord.Member):
    ws = get_warns(i.guild.id, membro.id)
    if not ws:
        await i.response.send_message(f"✅ **{membro}** não tem avisos.", ephemeral=True); return
    desc = "\n".join([f"`{n+1}.` {w['reason']}" for n,w in enumerate(ws)])
    await i.response.send_message(embed=discord.Embed(title=f"⚠️ Avisos de {membro.display_name}", description=desc, color=discord.Color.orange()), ephemeral=True)

@tree.command(name="historico", description="📜 Histórico de um membro")
@app_commands.checks.has_permissions(manage_messages=True)
async def historico(i: discord.Interaction, membro: discord.Member):
    data = get_xp(i.guild.id, membro.id); ws = get_warns(i.guild.id, membro.id)
    embed = discord.Embed(
        title=f"📜 Histórico de {membro.display_name}",
        description=f"**Nível:** {data.get('level',1)}\n**Mensagens:** {data.get('messages',0)}\n**Avisos:** {len(ws)}\n**Entrou:** {discord.utils.format_dt(membro.joined_at,'D') if membro.joined_at else 'N/A'}",
        color=0xFF6B9D)
    embed.set_thumbnail(url=membro.display_avatar.url)
    await i.response.send_message(embed=embed, ephemeral=True)


# ══════════════════════════════════════════
#  SORTEIOS
# ══════════════════════════════════════════

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Participar", style=discord.ButtonStyle.success, custom_id="giveaway_join")
    async def join(self, i: discord.Interaction, button: discord.ui.Button):
        g = giveaways.get(i.message.id)
        if not g:
            await i.response.send_message("❌ Sorteio não encontrado.", ephemeral=True); return
        if g.get("role_req"):
            role = i.guild.get_role(g["role_req"])
            if role and role not in i.user.roles:
                await i.response.send_message(f"❌ Você precisa do cargo {role.mention}.", ephemeral=True); return
        if i.user.id in g["participants"]:
            await i.response.send_message("✅ Você já está participando!", ephemeral=True); return
        g["participants"].append(i.user.id)
        await i.response.send_message(f"🎉 Participando! ({len(g['participants'])} inscritos)", ephemeral=True)


@tree.command(name="sorteio", description="🎁 Cria um sorteio")
@app_commands.checks.has_permissions(manage_guild=True)
async def sorteio(i: discord.Interaction, premio: str, minutos: int = 60, cargo: discord.Role = None):
    end = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutos)
    embed = discord.Embed(
        title="🎁 SORTEIO!", color=0xFF6B9D, timestamp=end,
        description=f"**Prêmio:** {premio}\n**Término:** <t:{int(end.timestamp())}:R>\n**Requisito:** {cargo.mention if cargo else 'Todos'}\n\nClique em 🎉 para participar!")
    embed.set_footer(text="Sorteio encerra em")
    await i.response.send_message(embed=embed, view=GiveawayView())
    msg = await i.original_response()
    giveaways[msg.id] = {"channel_id": i.channel.id, "prize": premio, "role_req": cargo.id if cargo else None, "participants": []}
    await asyncio.sleep(minutos * 60)
    g = giveaways.pop(msg.id, None)
    if not g or not g["participants"]:
        await i.channel.send("😢 Ninguém participou do sorteio."); return
    winner = i.guild.get_member(random.choice(g["participants"]))
    await i.channel.send(embed=discord.Embed(
        title="🎉 Resultado do Sorteio!",
        description=f"**Prêmio:** {premio}\n**Vencedor:** {winner.mention if winner else '?'} 🏆",
        color=discord.Color.gold()))


# ══════════════════════════════════════════
#  ENQUETES
# ══════════════════════════════════════════

@tree.command(name="enquete", description="📊 Cria uma enquete")
@app_commands.checks.has_permissions(manage_messages=True)
async def enquete(i: discord.Interaction, pergunta: str, opcao1: str, opcao2: str, opcao3: str = None, opcao4: str = None):
    opcoes = [o for o in [opcao1, opcao2, opcao3, opcao4] if o]
    emojis = ["1️⃣","2️⃣","3️⃣","4️⃣"]
    desc   = "\n".join([f"{emojis[n]} {o}" for n,o in enumerate(opcoes)])
    embed  = discord.Embed(title=f"📊 {pergunta}", description=desc, color=0xFF6B9D)
    embed.set_footer(text="Reaja para votar!")
    await i.response.send_message(embed=embed)
    msg = await i.original_response()
    for n in range(len(opcoes)): await msg.add_reaction(emojis[n])


# ══════════════════════════════════════════
#  ANÚNCIOS E LANÇAMENTOS
# ══════════════════════════════════════════

@tree.command(name="anunciar", description="📣 Posta um anúncio oficial")
@app_commands.checks.has_permissions(manage_guild=True)
async def anunciar(i: discord.Interaction, titulo: str, descricao: str, mencionar_todos: bool = False):
    ch = discord.utils.get(i.guild.channels, name="📣・anúncios")
    if not ch:
        await i.response.send_message("❌ Canal de anúncios não encontrado.", ephemeral=True); return
    embed = discord.Embed(title=f"📣 {titulo}", description=descricao, color=0xFF6B9D, timestamp=datetime.datetime.utcnow())
    embed.set_footer(text="Gato Comics • Anúncio Oficial 🐱")
    await ch.send(content="@everyone" if mencionar_todos else "", embed=embed)
    await i.response.send_message("✅ Anúncio postado!", ephemeral=True)


@tree.command(name="lancamento", description="🚀 Anuncia novo webtoon ou episódio")
@app_commands.checks.has_permissions(manage_guild=True)
async def lancamento(i: discord.Interaction, titulo: str, descricao: str, link: str, genero: str = None):
    ch = discord.utils.get(i.guild.channels, name="🚀・lançamentos")
    if not ch:
        await i.response.send_message("❌ Canal não encontrado.", ephemeral=True); return
    embed = discord.Embed(
        title=f"🚀 Novo Lançamento: {titulo}",
        description=f"{descricao}\n\n🔗 [Leia agora!]({link})",
        color=0xFF6B9D, timestamp=datetime.datetime.utcnow())
    embed.set_footer(text="Gato Comics 🐱")
    genero_map = {"ação":"⚔️ Fã de Ação","romance":"💕 Fã de Romance","terror":"👻 Fã de Terror","comédia":"😂 Fã de Comédia"}
    role = discord.utils.get(i.guild.roles, name=genero_map.get((genero or "").lower(), ""))
    await ch.send(content=role.mention if role else "", embed=embed)
    await i.response.send_message("✅ Lançamento anunciado!", ephemeral=True)


# ══════════════════════════════════════════
#  RANKING SEMANAL AUTOMÁTICO
# ══════════════════════════════════════════

@tasks.loop(hours=168)
async def weekly_ranking():
    for guild in bot.guilds:
        ch = discord.utils.get(guild.channels, name="🏆・ranking")
        if not ch: continue
        users = sorted(xp_data.get(str(guild.id),{}).items(),
                       key=lambda x:x[1].get("messages",0), reverse=True)[:10]
        if not users: continue
        medals = ["🥇","🥈","🥉"]+["🏅"]*7
        lines  = [f"{medals[n]} **{(guild.get_member(int(uid)) or type('_',(),{'display_name':f'ID {uid}'})).display_name}** — {d.get('messages',0)} msgs"
                  for n,(uid,d) in enumerate(users)]
        await ch.send(embed=discord.Embed(
            title="🏆 Ranking Semanal — Gato Comics",
            description="\n".join(lines), color=0xFF6B9D, timestamp=datetime.datetime.utcnow()))


# ══════════════════════════════════════════
#  EVENTOS
# ══════════════════════════════════════════

@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="🐱 Gato Comics"))
    weekly_ranking.start()
    print(f"✅ {bot.user} online!")


@bot.event
async def on_connect():
    bot.add_view(TicketCategoryView())
    bot.add_view(TicketCloseView())
    bot.add_view(GiveawayView())


@bot.event
async def on_member_join(member: discord.Member):
    guild  = member.guild
    novato = discord.utils.get(guild.roles, name="🆕 Novato")
    if novato: await member.add_roles(novato)
    ch = discord.utils.get(guild.channels, name="🎉・boas-vindas")
    if ch:
        embed = discord.Embed(
            title=f"🐱 Seja bem-vindo, {member.display_name}!",
            description=f"Que ótimo ter você aqui, {member.mention}! 🎉\n\nComplete o onboarding para ter acesso completo.",
            color=0xFF6B9D)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)


bot.run(TOKEN)