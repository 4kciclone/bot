import discord
from discord.ext import commands

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='setup_server', help='[Admin] Configura os canais e cargos do servidor Gato Comics.')
    @commands.has_permissions(administrator=True)
    async def setup_server(self, ctx):
        guild = ctx.guild
        await ctx.send("🚀 Iniciando a configuração do servidor da Gato Comics. Isso pode levar alguns segundos...")

        # 1. Criação de Cargos (Roles)
        # O discord cria cargos de baixo para cima na hierarquia visual se não especificarmos.
        # Vamos criar na ordem reversa, do menor pro maior privilégio, ou apenas criar e depois não ordenar estritamente (por agora)
        role_data = [
            {"name": "👑 Fundador / Sócio", "color": discord.Color.gold(), "hoist": True, "permissions": discord.Permissions(administrator=True)},
            {"name": "👑 Administrador", "color": discord.Color.orange(), "hoist": True, "permissions": discord.Permissions(administrator=True)},
            {"name": "🛡️ Moderador", "color": discord.Color.red(), "hoist": True, "permissions": discord.Permissions(manage_messages=True, kick_members=True, ban_members=True, moderate_members=True)},
            {"name": "🎧 Equipe de Suporte", "color": discord.Color.teal(), "hoist": True, "permissions": discord.Permissions(manage_messages=True)},
            {"name": "🎨 Artista Parceiro", "color": discord.Color.brand_green(), "hoist": True, "permissions": discord.Permissions(send_messages=True, read_messages=True)},
            {"name": "🖌️ Autor", "color": discord.Color.blue(), "hoist": True, "permissions": discord.Permissions(send_messages=True, read_messages=True)},
            {"name": "🌟 Super Fã (VIP)", "color": discord.Color.purple(), "hoist": True, "permissions": discord.Permissions(send_messages=True, read_messages=True)},
            {"name": "🚀 Server Booster", "color": discord.Color.magenta(), "hoist": True, "permissions": discord.Permissions(send_messages=True, read_messages=True)},
            {"name": "📖 Leitor (Membro)", "color": discord.Color.lighter_grey(), "hoist": True, "permissions": discord.Permissions(send_messages=True, read_messages=True)},
            {"name": "🔔 Ping de Anúncios", "color": discord.Color.light_grey(), "hoist": False, "permissions": discord.Permissions(send_messages=True, read_messages=True)},
            {"name": "🤖 Bots Parceiros", "color": discord.Color.dark_grey(), "hoist": False, "permissions": discord.Permissions.none()},
        ]

        created_roles = {}
        for r_data in role_data:
            role = discord.utils.get(guild.roles, name=r_data["name"])
            if not role:
                try:
                    role = await guild.create_role(
                        name=r_data["name"],
                        color=r_data["color"],
                        hoist=r_data["hoist"],
                        permissions=r_data["permissions"],
                        reason="Setup automático da Gato Comics"
                    )
                    created_roles[r_data["name"]] = role
                except Exception as e:
                    await ctx.send(f"⚠️ Erro ao criar cargo {r_data['name']}: {e}")
            else:
                created_roles[r_data["name"]] = role

        # Permissões específicas por cargo
        role_fundador = created_roles.get("👑 Fundador / Sócio")
        role_admin = created_roles.get("👑 Administrador")
        role_mod = created_roles.get("🛡️ Moderador")
        role_suporte = created_roles.get("🎧 Equipe de Suporte")
        role_autor = created_roles.get("🖌️ Autor")
        role_vip = created_roles.get("🌟 Super Fã (VIP)")
        role_bots = created_roles.get("🤖 Bots Parceiros")

        # Everyone role para esconder canais por padrão
        role_everyone = guild.default_role

        # 2. Criação de Categorias e Canais
        categories_data = [
            {
                "name": "📌 RECEPÇÃO",
                "overwrites": {
                    role_everyone: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                    role_bots: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                },
                "channels": [
                    {"name": "bem-vindo", "type": "text"},
                    {"name": "guia-da-comunidade", "type": "text"},
                    {"name": "anuncios", "type": "text"},
                    {"name": "atualizações-discord", "type": "text"}
                ]
            },
            {
                "name": "🏢 GATO COMICS HQ",
                "overwrites": {
                    role_everyone: discord.PermissionOverwrite(read_messages=False),
                    role_fundador: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_admin: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_mod: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_autor: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                },
                "channels": [
                    {"name": "reunião-diretoria", "type": "text"},
                    {"name": "produção-quadrinhos", "type": "text"},
                    {"name": "log-moderação", "type": "text"},
                    {"name": "Mesa de Reunião", "type": "voice"}
                ]
            },
            {
                "name": "🌟 CLUBE DE ASSINATURA",
                "overwrites": {
                    role_everyone: discord.PermissionOverwrite(read_messages=False),
                    role_fundador: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_admin: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_vip: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                },
                "channels": [
                    {"name": "spoilers-e-rascunhos", "type": "text"},
                    {"name": "downloads-exclusivos", "type": "text"},
                    {"name": "chat-vip", "type": "text"},
                    {"name": "Lounge VIP", "type": "voice"}
                ]
            },
            {
                "name": "📚 COMUNIDADE",
                "overwrites": {
                    role_everyone: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_bots: discord.PermissionOverwrite(read_messages=True, send_messages=False)
                },
                "channels": [
                    {"name": "chat-geral", "type": "text"},
                    {"name": "apresentações", "type": "text"},
                    {"name": "sugestões", "type": "text"},
                    {"name": "suporte", "type": "text"}
                ]
            },
            {
                "name": "🎭 ENTRETENIMENTO",
                "overwrites": {
                    role_everyone: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_bots: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                },
                "channels": [
                    {"name": "comandos-bots", "type": "text"},
                    {"name": "galeria-de-artes-ia", "type": "text"},
                    {"name": "Rádio Gato Comics", "type": "voice"}
                ]
            },
            {
                "name": "🎟️ TICKETS",
                "overwrites": {
                    role_everyone: discord.PermissionOverwrite(read_messages=False),
                    role_fundador: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_admin: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    role_suporte: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                },
                "channels": []
            }
        ]

        for cat_data in categories_data:
            category = discord.utils.get(guild.categories, name=cat_data["name"])
            
            # Limpar chaves None (caso um cargo tenha falhado em ser criado antes)
            clean_overwrites = {k: v for k, v in cat_data["overwrites"].items() if k is not None}
            
            if not category:
                try:
                    category = await guild.create_category(
                        name=cat_data["name"],
                        overwrites=clean_overwrites
                    )
                except Exception as e:
                    await ctx.send(f"⚠️ Erro ao criar categoria {cat_data['name']}: {e}")
                    continue

            for ch_data in cat_data["channels"]:
                # Verifica se o canal já existe na categoria
                existing_channel = discord.utils.get(category.channels, name=ch_data["name"])
                if not existing_channel:
                    try:
                        if ch_data["type"] == "text":
                            await guild.create_text_channel(name=ch_data["name"], category=category)
                        elif ch_data["type"] == "voice":
                            await guild.create_voice_channel(name=ch_data["name"], category=category)
                    except Exception as e:
                        await ctx.send(f"⚠️ Erro ao criar canal {ch_data['name']}: {e}")

        await ctx.send("✅ **Configuração do servidor Gato Comics concluída com sucesso!** Canais e Cargos foram criados.")

    @setup_server.error
    async def setup_server_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Você precisa ser um Administrador para rodar este comando.")

    @commands.command(name='setup_regras', help='[Admin] Envia o Embed de regras para o canal #guia-da-comunidade.')
    @commands.has_permissions(administrator=True)
    async def setup_regras(self, ctx):
        channel = discord.utils.get(ctx.guild.channels, name="guia-da-comunidade")
        if not channel:
            await ctx.send("❌ Canal #guia-da-comunidade não encontrado. Rode o `!setup_server` primeiro.")
            return

        embed = discord.Embed(
            title="📜 Guia Oficial da Gato Comics",
            description="Bem-vindo(a) à central de Webtoons e Mangás BR! Siga as nossas diretrizes para mantermos nossa comunidade incrível e saudável.",
            color=discord.Color.brand_green()
        )
        embed.add_field(
            name="1️⃣ Respeito em Primeiro Lugar",
            value="Trate os membros, artistas e staff com respeito. Não toleramos discurso de ódio, assédio ou preconceito.",
            inline=False
        )
        embed.add_field(
            name="2️⃣ Evite Spoilers",
            value="Ninguém gosta de surpresas estragadas! Use as barras de `||spoiler||` no chat se for falar de lançamentos recentes.",
            inline=False
        )
        embed.add_field(
            name="3️⃣ Propriedade Intelectual",
            value="Respeite os direitos dos criadores. Não poste links de pirataria de nosso conteúdo ou outras obras externas.",
            inline=False
        )
        embed.add_field(
            name="4️⃣ Cada Bot no seu Quadrado",
            value="Use bots de música, jogos e imagens **apenas** na categoria **🎭 ENTRETENIMENTO** e em seus devidos canais.",
            inline=False
        )
        embed.add_field(
            name="5️⃣ Suporte e Bugs",
            value="Problemas de leitura ou pagamento? Abra um ticket em **#suporte** na aba **🎟️ TICKETS** para falar diretamente com a Equipe.",
            inline=False
        )
        embed.set_footer(text="Gato Comics - Conectando Criadores e Fãs!")
        
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        try:
            await channel.purge(limit=5)
            await channel.send(embed=embed)
            await ctx.send(f"✅ Regras enviadas com sucesso para o canal <#{channel.id}>!")
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao postar regras: {e}")

    @setup_regras.error
    async def setup_regras_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Você precisa ser um Administrador para rodar este comando.")

async def setup(bot):
    await bot.add_cog(Setup(bot))
