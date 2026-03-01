import discord
from discord import app_commands
import aiohttp
from config import *

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

conversation_history = {}  # {user_id: [messages]}

async def call_nvidia(messages: list, max_tokens=500) -> str:
    if not NVIDIA_API_KEY:
        return "❌ NVIDIA API Key não configurada no .env"
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "meta/llama-3.1-8b-instruct",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }
            async with session.post(
                NVIDIA_API_URL,
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    return f"❌ Erro na API: {resp.status}"
    except Exception as e:
        return f"❌ Erro: {e}"


def setup_commands(tree: app_commands.CommandTree, bot):

    @tree.command(name="perguntar", description="🤖 Faça uma pergunta para o assistente IA da Gato Comics")
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.user.id)
    async def perguntar(interaction: discord.Interaction, pergunta: str):
        await interaction.response.defer()
        uid = str(interaction.user.id)

        # Histórico de conversa (até 5 mensagens anteriores)
        if uid not in conversation_history:
            conversation_history[uid] = []

        conversation_history[uid].append({"role": "user", "content": pergunta})
        if len(conversation_history[uid]) > 10:
            conversation_history[uid] = conversation_history[uid][-10:]

        messages = [
            {
                "role": "system",
                "content": (
                    "Você é o assistente oficial da Gato Comics, uma editora digital de webtoons brasileira. "
                    "Você é simpático, conhece muito sobre webtoons, mangás, animes e cultura pop. "
                    "Responda sempre em português brasileiro de forma clara e amigável. "
                    "Se perguntarem sobre a Gato Comics, diga que é a maior editora de webtoons do Brasil. "
                    "Mantenha respostas concisas (máximo 3 parágrafos)."
                )
            }
        ] + conversation_history[uid]

        resposta = await call_nvidia(messages)
        conversation_history[uid].append({"role": "assistant", "content": resposta})

        embed = discord.Embed(
            title="🤖 Assistente Gato Comics",
            description=f"**Você:** {pergunta}\n\n**Assistente:** {resposta}",
            color=0xFF6B9D
        )
        embed.set_footer(text="Powered by NVIDIA NIM 🐱")
        await interaction.followup.send(embed=embed)


    @tree.command(name="limparchat", description="🗑️ Limpa seu histórico com o assistente")
    async def limpar_chat(interaction: discord.Interaction):
        conversation_history.pop(str(interaction.user.id), None)
        await interaction.response.send_message("✅ Histórico de conversa limpo!", ephemeral=True)