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
            # Novos cargos de orquestração
            {"name": "🎧 DJ",                       "color": discord.Color.teal(),                  "hoist": True},
            {"name": "💍 Waifu Collector",          "color": discord.Color.from_rgb(255,192,203),   "hoist": False},
            {"name": "🖌️ Mestre do Gartic",         "color": discord.Color.from_rgb(255,255,0),     "hoist": False},
            {"name": "🐸 Dank Member",              "color": discord.Color.dark_green(),            "hoist": False},
            # Conquistas
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
        dj_role = cr["🎧 DJ"]; waifu_role = cr["💍 Waifu Collector"]
        
        await guild.default_role.edit(permissions=discord.Permissions(view_channel=False))

        def ow_default():
            base = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                novato: discord.PermissionOverwrite(view_channel=True, send_messages=False),
                leitor: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                mod:    discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True),
                admin:  discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
                owner:  discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
            }
            # Bloquear bots externos de canais comuns (Poluentes)
            external_bots = [411916947773587459, 432610292342587392, 487328045275938828, 270904126974590976]
            for bid in external_bots:
                bot_user = guild.get_member(bid)
                if bot_user:
                    base[bot_user] = discord.PermissionOverwrite(view_channel=False)
            return base
        
        def ow_bot_dedicated(bot_id: int):
            # Tenta encontrar o bot no servidor para dar permissão específica
            overwrites = ow_default()
            bot_member = guild.get_member(bot_id)
            if bot_member:
                overwrites[bot_member] = discord.PermissionOverwrite(
                    view_channel=True, 
                    send_messages=True, 
                    embed_links=True, 
                    attach_files=True, 
                    use_external_emojis=True,
                    connect=True,
                    speak=True
                )
            return overwrites

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
                ("🤖・comandos-bot",       "text", "Use os comandos do Gato Comics aqui!",ow_default()),
                ("😂・memes-e-cultura-pop", "text", "Memes e trends.",                 ow_default()),
                ("🎮・off-topic",           "text", "Qualquer assunto aqui!",          ow_default()),
                ("📊・enquetes",            "text", "Enquetes da comunidade.",         ow_default()),
                ("🎁・sorteios",            "text", "Sorteios oficiais.",              ow_default()),
            ]),
            ("💍 MUDAE", [
                ("💍・mudae-waifus",    "text", "Colecione seus personagens aqui!",   ow_bot_dedicated(432610292342587392)),
                ("💍・casamentos",      "text", "Log de casamentos e divórcios.",     ow_bot_dedicated(432610292342587392)),
            ]),
            ("🎨 GARTIC & FUN", [
                ("🎨・gartic-game",     "text", "Desenhe e adivinhe com o Gartic!",   ow_bot_dedicated(487328045275938828)),
                ("🐸・dank-memer",      "text", "Economia e memes com o Dank!",       ow_bot_dedicated(270904126974590976)),
            ]),
            ("🎵 MÚSICA", [
                ("🎵・pedir-musica",    "text",  "Use comandos de música aqui.",      ow_bot_dedicated(411916947773587459)),
                ("🔊 Sala de Música 1", "voice", "",                                  ow_bot_dedicated(411916947773587459)),
                ("🔊 Sala de Música 2", "voice", "",                                  ow_bot_dedicated(411916947773587459)),
            ]),
            ("🔊 VOZ GERAL", [
                ("🔊 Sala Geral",       "voice", "",                                  ow_default()),
                ("📚 Clube de Leitura", "voice", "",                                  ow_default()),
                ("🎮 Gaming",           "voice", "",                                  ow_default()),
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
            cat = discord.utils.get(guild.categories, name=cat_name)
            if not cat:
                cat = await guild.create_category(cat_name, overwrites=ow_default())
            else:
                # Sincroniza overwrites da categoria
                await cat.edit(overwrites=ow_default())

            for ch_name, ch_type, topic, overwrites in channels:
                ch = discord.utils.get(guild.channels, name=ch_name)
                if not ch:
                    if ch_type == "text":
                        ch = await guild.create_text_channel(ch_name, category=cat, topic=topic, overwrites=overwrites)
                    else:
                        ch = await guild.create_voice_channel(ch_name, category=cat, overwrites=overwrites)
                    logs.append(f"Criado: {ch_name}")
                else:
                    # Sincroniza overwrites do canal existente
                    await ch.edit(overwrites=overwrites, category=cat)
                    logs.append(f"Sincronizado: {ch_name}")

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
        rules_mention = rules_ch.mention if rules_ch else "#regras"
        if wch:
            embed = discord.Embed(
                title="🐱 Bem-vindo à Gato Comics!",
                description=(
                    "Olá! Você chegou na comunidade oficial da **Gato Comics** 🇧🇷\n"
                    "A editora digital de webtoons 100% brasileira!\n\n"
                    f"📋 Leia as {rules_mention}\n"
                    "🎭 Se apresente no canal de apresentações!\n"
                    "🎮 Jogue com Mudae, Gartic e ganhe XP!"
                ),
                color=0xFF6B9D
            )
            embed.set_footer(text="Gato Comics • A sua editora de webtoons 🐱")
            await wch.send(embed=embed)

        # Painel de ticket
        if ticket_ch:
            from modules.tickets import send_ticket_panel
            await send_ticket_panel(ticket_ch)

        # Atribuição automática de cargos para os bots auxiliares
        bot_assignments = [
            (411916947773587459, cr.get("🎧 DJ")),                # Jockie Music
            (432610292342587392, cr.get("💍 Waifu Collector")),   # Mudae
            (487328045275938828, cr.get("🖌️ Mestre do Gartic")),  # Gartic
            (270904126974590976, cr.get("🐸 Dank Member")),       # Dank Memer
        ]

        for bot_id, role in bot_assignments:
            if role:
                member = guild.get_member(bot_id)
                if member:
                    try:
                        await member.add_roles(role)
                        logs.append(f"Cargo atribuído ao bot: {member.name}")
                    except Exception as e:
                        logs.append(f"Erro ao dar cargo a {bot_id}: {str(e)[:30]}")

        # Caso existam múltiplos Jockie Music (instâncias), procurar por nome
        for m in guild.members:
            if m.bot and "Jockie Music" in m.name and m.id != 411916947773587459:
                dj_role = cr.get("🎧 DJ")
                if dj_role:
                    try: await m.add_roles(dj_role)
                    except: pass

        embed_done = discord.Embed(
            title="✅ Orquestração Gato Comics concluída!",
            description="Todos os cargos e canais foram configurados. Agora convide os bots auxiliares clicando em `/ajuda`!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed_done, ephemeral=True)

    @tree.command(name="cleanup", description="🧨 DELETA TODOS os canais e categorias do servidor (APENAS DONO)")
    @app_commands.checks.has_permissions(administrator=True)
    async def cleanup(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        deleted_count = 0

        # Deletar todos os canais de texto, voz e categorias
        for channel in guild.channels:
            try:
                # Evita erro ao tentar deletar o canal onde a resposta está sendo enviada no meio do processo
                # Mas como é defered, podemos tentar deletar tudo.
                await channel.delete()
                deleted_count += 1
            except Exception as e:
                print(f"Erro ao deletar {channel.name}: {e}")

        # Como deletamos o canal de interação, não conseguimos enviar o followup se ele for deletado.
        # Mas para "deletar todos", o sacrifício é necessário.
        print(f"✅ Limpeza total concluída: {deleted_count} itens removidos.")

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

        embed.set_footer(text="Gato Comics • A sua editora de webtoons 🐱")
        await interaction.response.send_message(embed=embed)

    @tree.command(name="admin-links", description="🔗 Links de convite para os bots auxiliares (APENAS STAFF)")
    @staff_only()
    async def admin_links(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔗 Links de Orquestração",
            description="Use os links abaixo para convidar os bots recomendados. **Apenas administradores podem ver esta mensagem.**",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎵 Jockie Music", value="[Convidar](https://www.jockiemusic.com/invite)", inline=True)
        embed.add_field(name="💎 Mudae", value="[Convidar](https://discord.com/oauth2/authorize?client_id=432610292342587392&scope=bot&permissions=537213952)", inline=True)
        embed.add_field(name="🎨 Gartic", value="[Convidar](https://discord.com/oauth2/authorize?client_id=487328045275938828&scope=bot&permissions=277025810432)", inline=True)
        embed.add_field(name="🐸 Dank Memer", value="[Convidar](https://discord.com/oauth2/authorize?client_id=270904126974590976&scope=bot&permissions=8)", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
