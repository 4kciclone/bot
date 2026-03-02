import discord
from discord import app_commands
import aiohttp
from config import *

def setup_commands(tree: app_commands.CommandTree, bot):

    @tree.command(name="setup", description="⚙️ Configura o servidor completo da Gato Comics")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        logs  = []

        await interaction.followup.send("⏳ Iniciando setup completo...", ephemeral=True)

        roles_cfg = [
            {"name": "👑 Owner",                   "color": discord.Color.gold(),                  "hoist": True},
            {"name": "⚙️ Admin",                   "color": discord.Color.red(),                   "hoist": True},
            {"name": "🛡️ Moderador",               "color": discord.Color.blue(),                  "hoist": True},
            {"name": "🎨 Criador Parceiro",         "color": discord.Color.purple(),                "hoist": True},
            {"name": "✍️ Escritor Parceiro",        "color": discord.Color.green(),                 "hoist": True},
            {"name": "⭐ Veterano",                 "color": discord.Color.orange(),                "hoist": True},
            {"name": "💎 Leitor VIP",               "color": discord.Color.from_rgb(255,105,180),   "hoist": True},
            {"name": "📖 Leitor",                   "color": discord.Color.light_grey(),             "hoist": False},
            {"name": "🆕 Novato",                   "color": discord.Color.default(),               "hoist": False},
            {"name": "🌟 Destaque",                 "color": discord.Color.from_rgb(255,215,0),     "hoist": False},
            {"name": "💜 Apoiador",                 "color": discord.Color.from_rgb(148,0,211),     "hoist": False},
            {"name": "🔥 Lenda",                    "color": discord.Color.from_rgb(255,69,0),      "hoist": False},
            {"name": "🎭 Contador de Histórias",    "color": discord.Color.from_rgb(0,191,255),     "hoist": False},
            {"name": "⚔️ Fã de Ação",               "color": discord.Color.from_rgb(220,50,50),     "hoist": False},
            {"name": "💕 Fã de Romance",            "color": discord.Color.from_rgb(255,150,180),   "hoist": False},
            {"name": "👻 Fã de Terror",             "color": discord.Color.from_rgb(100,60,120),    "hoist": False},
            {"name": "😂 Fã de Comédia",            "color": discord.Color.from_rgb(255,210,50),    "hoist": False},
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
        def ow_stats():
            return {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                novato: discord.PermissionOverwrite(view_channel=True, connect=False),
                leitor: discord.PermissionOverwrite(view_channel=True, connect=False),
                mod:    discord.PermissionOverwrite(view_channel=True, connect=False),
                admin:  discord.PermissionOverwrite(view_channel=True, connect=False),
                owner:  discord.PermissionOverwrite(view_channel=True, connect=False),
            }

        structure = [
            ("📌 INÍCIO", [
                ("📋・regras",       "text",  "Leia antes de participar.",           ow_readonly()),
                ("📣・anúncios",      "text",  "Novidades oficiais da Gato Comics.",  ow_readonly()),
                ("🎉・boas-vindas",   "text",  "Boas-vindas automáticas.",            ow_readonly()),
                ("🎭・apresentações", "text",  "Se apresente para a comunidade!",     ow_default()),
            ]),
            ("📖 WEBTOONS", [
                ("🚀・lançamentos",     "text", "Novos episódios e títulos.",         ow_readonly()),
                ("💬・discussão-geral", "text", "Papo geral sobre webtoons.",         ow_default()),
                ("⭐・recomendações",   "text", "Indique seus webtoons favoritos!",   ow_default()),
                ("🔍・spoilers",        "text", "Discussão com spoilers. Cuidado!",   ow_default()),
            ]),
            ("🎨 CRIADORES", [
                ("🖼️・portfólio",         "text", "Mostre seus trabalhos.",           ow_default()),
                ("🛠️・tutoriais-e-dicas",  "text", "Dicas de criação de webtoons.",   ow_default()),
                ("🤝・oportunidades",      "text", "Vagas e parcerias oficiais.",      ow_readonly()),
            ]),
            ("💬 COMUNIDADE", [
                ("🗨️・bate-papo",          "text", "Conversa geral.",                 ow_default()),
                ("😂・memes-e-cultura-pop", "text", "Memes e trends.",                 ow_default()),
                ("🎮・off-topic",           "text", "Qualquer assunto aqui!",          ow_default()),
                ("📊・enquetes",            "text", "Enquetes da comunidade.",         ow_default()),
                ("🎁・sorteios",            "text", "Sorteios oficiais.",              ow_default()),
            ]),
            ("🎮 JOGOS", [
                ("🎮・jogos",           "text", "Use os comandos de jogos aqui!",     ow_default()),
                ("🏅・placar",          "text", "Placar dos jogos e torneios.",        ow_readonly()),
            ]),
            ("🎵 VOZ & MÚSICA", [
                ("🎵・comandos-musica", "text",  "Use comandos de música aqui.",      ow_default()),
                ("🔊 Sala Geral",       "voice", "",                                  ow_default()),
                ("📚 Clube de Leitura", "voice", "",                                  ow_default()),
                ("🎮 Gaming",           "voice", "",                                  ow_default()),
                ("🎵 Música",           "voice", "",                                  ow_default()),
            ]),
            ("🏆 RANKING", [
                ("🏆・ranking",    "text", "Top membros mais ativos.",               ow_readonly()),
                ("⭐・conquistas", "text", "Conquistas e subidas de nível.",         ow_readonly()),
            ]),
            ("🎫 SUPORTE", [
                ("🎫・abrir-ticket", "text", "Clique para abrir um ticket.",          ow_readonly()),
                ("📋・log-tickets",  "text", "Log de tickets fechados.",              ow_staff()),
                ("🔨・log-moderação","text", "Log de ações de moderação.",            ow_staff()),
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

        # Canais de estatísticas (voice channels somente leitura)
        stats_cat = discord.utils.get(guild.categories, name=STATS_CATEGORY)
        if not stats_cat:
            stats_cat = await guild.create_category(STATS_CATEGORY, overwrites=ow_stats())
            stats_channels = [
                f"👥 Membros: {guild.member_count}",
                f"🟢 Online: 0",
                f"🎫 Tickets: 0",
            ]
            for sc in stats_channels:
                await guild.create_voice_channel(sc, category=stats_cat, overwrites=ow_stats())
            logs.append("Canais de estatísticas criados!")

        # Habilitar Comunidade
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
            logs.append(f"Comunidade (manual): {str(e)[:50]}")

        # Onboarding via API
        try:
            onboarding = {
                "prompts": [
                    {
                        "id": "1", "type": 1, "title": "Você é...?",
                        "single_select": True, "required": True, "in_onboarding": True,
                        "options": [
                            {"id": "101", "title": "📖 Leitor de Webtoons",    "role_ids": [str(cr["📖 Leitor"].id)]},
                            {"id": "102", "title": "🎨 Artista / Criador",     "role_ids": [str(cr["🎨 Criador Parceiro"].id)]},
                            {"id": "103", "title": "✍️ Escritor / Roteirista", "role_ids": [str(cr["✍️ Escritor Parceiro"].id)]},
                            {"id": "104", "title": "👀 Só explorando",         "role_ids": [str(cr["🆕 Novato"].id)]},
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
                "enabled": True, "mode": 1
            }
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"https://discord.com/api/v10/guilds/{guild.id}/onboarding",
                    headers={"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"},
                    json=onboarding
                ) as resp:
                    logs.append("Onboarding configurado!" if resp.status == 200 else f"Onboarding: erro {resp.status}")
        except Exception as e:
            logs.append(f"Onboarding: {str(e)[:50]}")

        # Boas vindas
        wch = discord.utils.get(guild.channels, name=WELCOME_CHANNEL)
        if wch:
            embed = discord.Embed(
                title="🐱 Bem-vindo à Gato Comics!",
                description=(
                    "Olá! Você chegou na comunidade oficial da **Gato Comics** 🇧🇷\n"
                    "A editora digital de webtoons 100% brasileira!\n\n"
                    f"📋 Leia as {rules_ch.mention}\n"
                    "🎭 Se apresente no canal de apresentações!\n"
                    "🎮 Jogue, ganhe XP e suba de nível!"
                ),
                color=0xFF6B9D
            )
            embed.set_footer(text="Gato Comics • A sua editora de webtoons 🐱")
            await wch.send(embed=embed)

        # Painel de ticket
        if ticket_ch:
            from modules.tickets import send_ticket_panel
            await send_ticket_panel(ticket_ch)

        embed_done = discord.Embed(
            title="✅ Setup Gato Comics concluído!",
            description="\n".join([f"✅ {l}" for l in logs[-25:]]),
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed_done, ephemeral=True)

    @tree.command(name="cleanup", description="🧹 Remove todos os canais e categorias criados pelo setup (Dono/Admin)")
    @app_commands.checks.has_permissions(administrator=True)
    async def cleanup(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        deleted_count = 0

        # Categorias e canais conhecidos do setup
        targets = [
            "📌 INÍCIO", "📖 WEBTOONS", "🎨 CRIADORES", "💬 COMUNIDADE",
            "🎮 JOGOS", "🎵 VOZ & MÚSICA", "🏆 RANKING", "🎫 SUPORTE",
            STATS_CATEGORY
        ]

        # Deletar canais dentro dessas categorias primeiro
        for category in guild.categories:
            if category.name in targets:
                for channel in category.channels:
                    try:
                        await channel.delete()
                        deleted_count += 1
                    except: pass
                try:
                    await category.delete()
                    deleted_count += 1
                except: pass

        await interaction.followup.send(f"✅ Limpeza concluída! **{deleted_count}** itens removidos.", ephemeral=True)

    @tree.command(name="ajuda", description="❓ Veja todos os comandos e funcionalidades da Gato Comics")
    async def ajuda(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🐱 Guia da Gato Comics",
            description="Aqui estão as funcionalidades principais do nosso bot e recomendações para o servidor!",
            color=0xFF6B9D
        )

        embed.add_field(
            name="🤖 Inteligência Artificial",
            value="O bot monitora o chat e responde automaticamente com nossa IA. Basta conversar!",
            inline=False
        )

        embed.add_field(
            name="📊 XP & Níveis",
            value="`/perfil` - Veja seu nível, XP e conquistas.\n`/ranking` - Veja os membros mais ativos.",
            inline=True
        )

        embed.add_field(
            name="🎫 Suporte & Tickets",
            value="Comando `/setup` cria o painel de tickets.",
            inline=True
        )

        embed.add_field(
            name="🎵 Música",
            value="Recomendamos o **Jockie Music** para a melhor experiência sonora.",
            inline=False
        )

        embed.add_field(
            name="🎮 Jogos",
            value="**Mudae**: Colecione personagens.\n**Gartic**: Desenho em grupo.\n**Dank Memer**: Economia e zoeira.",
            inline=False
        )

        # Botões de link
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🎵 Jockie Music", url="https://www.jockiemusic.com/invite", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="💎 Mudae", url="https://discord.com/oauth2/authorize?client_id=432610292342587392&scope=bot&permissions=537213952", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="🎨 Gartic", url="https://discord.com/oauth2/authorize?client_id=694921670984138762&scope=bot&permissions=277025810432", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="🐸 Dank Memer", url="https://discord.com/oauth2/authorize?client_id=270904126974590976&scope=bot&permissions=8", style=discord.ButtonStyle.link))

        embed.set_footer(text="Gato Comics • A sua editora de webtoons 🐱")
        await interaction.response.send_message(embed=embed, view=view)
