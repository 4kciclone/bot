import discord
from discord.ext import commands

class BotPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Botões de Convite

        # 🎵 Música
        self.add_item(discord.ui.Button(
            label="Música (Jockie Music)", 
            style=discord.ButtonStyle.link, 
            url="https://discord.com/oauth2/authorize?client_id=412153375836962828&permissions=8&scope=bot",
            emoji="🎵"
        ))

        # 🎮 Jogos
        self.add_item(discord.ui.Button(
            label="Gacha (Mudae)", 
            style=discord.ButtonStyle.link, 
            url="https://discord.com/oauth2/authorize?client_id=432610292342587392&permissions=8&scope=bot",
            emoji="🎮"
        ))

        # 🎨 Artes (Midjourney/Niji)
        self.add_item(discord.ui.Button(
            label="Artes IA (Niji Journey)", 
            style=discord.ButtonStyle.link, 
            url="https://discord.com/oauth2/authorize?client_id=1022952195194425444&permissions=8&scope=bot",
            emoji="🎨"
        ))

class BotsInvite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='painel_bots', help='[Admin] Exibe um painel para convidar bots de terceiros.')
    @commands.has_permissions(administrator=True)
    async def painel_bots(self, ctx):
        embed = discord.Embed(
            title="🤖 Painel de Integração de Bots",
            description=(
                "A Gato Comics precisa de muito entretenimento para nossa comunidade!\n\n"
                "Para configurar funcionalidades extras nos canais de **🎭 ENTRETENIMENTO**, "
                "clique nos botões abaixo para adicionar os bots recomendados ao servidor.\n\n"
                "⚠️ **Atenção Administradores:** Após adicionar o bot, lembre-se de configurar o "
                "cargo `🤖 Bots Parceiros` para eles, caso queiram padronizar as cores e permissões."
            ),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Gato Comics - Conectando Criadores e Fãs")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None)

        await ctx.send(embed=embed, view=BotPanel())

    @painel_bots.error
    async def painel_bots_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Você precisa ser um Administrador para rodar este comando.")

async def setup(bot):
    await bot.add_cog(BotsInvite(bot))
