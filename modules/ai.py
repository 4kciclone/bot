import discord
from discord.ext import commands
import aiohttp
import os
import io
import base64

class ArtAI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium"
        self.api_key = os.getenv("NVIDIA_API_KEY")

    @commands.group(name='gato_ai', invoke_without_command=True, help='Gera imagens usando Inteligência Artificial da NVIDIA.')
    async def gato_ai(self, ctx):
        embed = discord.Embed(
            title="🤖 Gato Comics AI",
            description=(
                "Nosso próprio modelo de Inteligência Artificial nativo está online!\n\n"
                "Use o comando `!gato_ai gerar <seu texto aqui>`.\n"
                "Para manter a organização, o comando funciona exclusivamente no canal <#galeria-de-artes-ia>."
            ),
            color=discord.Color.brand_green()
        )
        await ctx.send(embed=embed)

    @gato_ai.command(name='gerar')
    async def gerar(self, ctx, *, prompt: str):
        # Proteção: Rodar apenas na categoria certa ou canal certo
        if "galeria-de-artes-ia" not in ctx.channel.name:
            await ctx.send("❌ Por favor, use este comando apenas no canal dedicado para Artes de IA para manter a comunidade organizada!")
            return

        if not self.api_key:
            await ctx.send("❌ A chave da API da NVIDIA NIM não está configurada no `.env`.")
            return

        # Aviso visual para o usuário
        msg = await ctx.send(f"⏳ Processando sua ideia nas GPUs da NVIDIA, `{ctx.author.name}`... Aguarde!")

        async with ctx.typing():
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            # Stable Diffusion 3 NIM Configuration
            payload = {
                "prompt": prompt
            }

            try:
                # Usar aiohttp para não travar o bot enquanto gera
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.api_url, headers=headers, json=payload, timeout=60) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "image" in data:
                                # A NVIDIA NIM retorna os bytes da imagem em base64 na chave 'image'
                                image_data = base64.b64decode(data["image"])
                                image_file = discord.File(io.BytesIO(image_data), filename="gato_comics_ai.png")
                                await msg.delete() # Remove a mensagem de aviso
                                await ctx.send(f"🎨 **Ideia:** `{prompt}`\n👤 **Criação de:** {ctx.author.mention}", file=image_file)
                            else:
                                await msg.edit(content="⚠️ A API respondeu com sucesso, mas o formato da imagem não foi encontrado.")
                        elif response.status == 422:
                            await msg.edit(content="❌ Erro 422: O texto enviado foi rejeitado pela API da NVIDIA. Tente palavras diferentes.")
                        else:
                            error_text = await response.text()
                            await msg.edit(content=f"⚠️ Falha na comunicação com a NVIDIA (Erro {response.status}).")
            except Exception as e:
                await msg.edit(content=f"❌ Ocorreu um erro interno durante a geração: {e}")

async def setup(bot):
    await bot.add_cog(ArtAI(bot))
