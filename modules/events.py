import discord
from discord.ext import commands

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # 1. Encontrar o canal de boas-vindas
        welcome_channel = discord.utils.get(member.guild.text_channels, name="bem-vindo")
        if not welcome_channel:
            return

        # 2. Dar o cargo de leitor automaticamente
        reader_role = discord.utils.get(member.guild.roles, name="📖 Leitor (Membro)")
        
        try:
            if reader_role:
                await member.add_roles(reader_role, reason="Auto-role do Bot Gato Comics")
        except Exception as e:
            print(f"Erro ao dar cargo automático: {e}")

        # 3. Montar a mensagem de Boas-vindas premium
        embed = discord.Embed(
            title=f"Bem-vindo(a) à Gato Comics!",
            description=(
                f"Olá {member.mention}! Chega mais, pegue um café ☕ e sinta-se em casa.\n\n"
                "Para começar, dá uma lida no canal de regras e acompanhe os `#anuncios`!\n\n"
                "Aproveite as webtoons, participe da comunidade e se prepare para os melhores mangás brasileiros!"
            ),
            color=discord.Color.gold()
        )
        
        # Puxa a foto de perfil da pessoa se ela tiver, se não fica a padrão
        if member.display_avatar:
             embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.set_footer(text=f"Agora somos {member.guild.member_count} criadores e leitores!")
        embed.set_image(url="https://media.giphy.com/media/xT0xezQGU5xCDJuCPe/giphy.gif") # Gif divertido genérico como exemplo

        await welcome_channel.send(content=f"🎉 {member.mention}", embed=embed)

async def setup(bot):
    await bot.add_cog(Events(bot))
