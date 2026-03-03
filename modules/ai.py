import discord
from discord.ext import commands

class ArtAI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='gato_ai', invoke_without_command=True, help='[Em Breve] Integração base para Artes e IA da Gato Comics.')
    async def gato_ai(self, ctx):
        embed = discord.Embed(
            title="🤖 Gato Comics AI",
            description=(
                "Em breve, nosso próprio modelo de IA poderá gerar imagens baseadas "
                "nas IPs e personagens originais da Gato Comics!\n\n"
                "Para saber mais sobre o progresso, fique de olho no canal `#anuncios`."
            ),
            color=discord.Color.brand_green()
        )
        await ctx.send(embed=embed)

    @gato_ai.command(name='gerar')
    async def gerar(self, ctx, *, prompt: str):
        # Esqueleto para futura integração com API de imagem (DALL-E, Stable Diffusion, etc)
        await ctx.send(f"🎨 **Entendido!** Você quer gerar uma arte sobre: `{prompt}`\n\n*Nota: Esta funcionalidade ainda está em desenvolvimento pelo time de tecnologia da Gato Comics.*")

async def setup(bot):
    await bot.add_cog(ArtAI(bot))
