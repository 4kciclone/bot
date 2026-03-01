import discord
from discord import app_commands
import datetime
import aiohttp
from config import *

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

async def ai_analyze(text: str) -> str:
    """Analisa texto com NVIDIA NIM para detectar conteúdo problemático."""
    if not NVIDIA_API_KEY:
        return "ok"
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "meta/llama-3.1-8b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Você é um moderador de comunidade Discord. Analise a mensagem e responda APENAS com:\n"
                            "'ok' se for uma mensagem normal\n"
                            "'warn' se for levemente ofensiva ou suspeita\n"
                            "'delete' se for muito ofensiva, spam ou prejudicial\n"
                            "Responda SOMENTE com uma dessas palavras, nada mais."
                        )
                    },
                    {"role": "user", "content": text[:500]}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            async with session.post(
                NVIDIA_API_URL,
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip().lower()
    except:
        pass
    return "ok"


async def log_mod_action(guild: discord.Guild, action: str, target: discord.Member,
                          moderator: discord.Member, reason: str, color=discord.Color.red()):
    """Registra ação de moderação no canal de log."""
    log_ch = discord.utils.get(guild.channels, name=LOG_MOD_CHANNEL)
    if not log_ch:
        return
    embed = discord.Embed(
        title=f"🔨 {action}",
        color=color,
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="👤 Usuário",    value=f"{target.mention} (`{target}`)",    inline=True)
    embed.add_field(name="🛡️ Moderador", value=f"{moderator.mention}",              inline=True)
    embed.add_field(name="📝 Motivo",     value=reason,                              inline=False)
    embed.set_thumbnail(url=target.display_avatar.url)
    await log_ch.send(embed=embed)


def setup_commands(tree: app_commands.CommandTree, bot):

    # ── Moderação inteligente com IA ──
    @bot.event
    async def on_message_ai(message):
        """Analisa mensagens suspeitas com IA. Chamado pelo bot principal."""
        if message.author.bot or not message.guild: return
        if len(message.content) < 10: return

        result = await ai_analyze(message.content)

        if result == "delete":
            try:
                await message.delete()
                await message.channel.send(
                    f"🤖 {message.author.mention} sua mensagem foi removida pela moderação automática.",
                    delete_after=8
                )
                total = add_warn(message.guild.id, message.author.id, "Auto-warn: conteúdo removido por IA", "Bot")
                await log_mod_action(message.guild, "Auto-Moderação (IA)", message.author,
                                     message.guild.me, "Conteúdo removido automaticamente pela IA")
                if total >= WARNS_BAN:
                    await message.author.ban(reason=f"Auto-ban: {total} warns")
                elif total >= WARNS_MUTE:
                    until = discord.utils.utcnow() + datetime.timedelta(hours=1)
                    await message.author.timeout(until, reason=f"Auto-mute: {total} warns")
            except: pass

        elif result == "warn":
            await message.channel.send(
                f"⚠️ {message.author.mention} cuidado com o tom da sua mensagem!",
                delete_after=10
            )


    @tree.command(name="kick", description="👢 Expulsa um membro")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
        await membro.kick(reason=motivo)
        await interaction.response.send_message(f"👢 **{membro}** expulso.", ephemeral=True)
        await log_mod_action(interaction.guild, "Kick", membro, interaction.user, motivo, discord.Color.orange())


    @tree.command(name="ban", description="🔨 Bane um membro")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
        await membro.ban(reason=motivo)
        await interaction.response.send_message(f"🔨 **{membro}** banido.", ephemeral=True)
        await log_mod_action(interaction.guild, "Ban", membro, interaction.user, motivo, discord.Color.red())


    @tree.command(name="mute", description="🔇 Silencia um membro")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(interaction: discord.Interaction, membro: discord.Member, minutos: int = 10, motivo: str = "Sem motivo"):
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutos)
        await membro.timeout(until, reason=motivo)
        await interaction.response.send_message(f"🔇 **{membro}** silenciado por {minutos}min.", ephemeral=True)
        await log_mod_action(interaction.guild, f"Mute ({minutos}min)", membro, interaction.user, motivo, discord.Color.yellow())


    @tree.command(name="unmute", description="🔊 Remove silêncio")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(interaction: discord.Interaction, membro: discord.Member):
        await membro.timeout(None)
        await interaction.response.send_message(f"🔊 Silêncio removido de **{membro}**.", ephemeral=True)
        await log_mod_action(interaction.guild, "Unmute", membro, interaction.user, "Silêncio removido", discord.Color.green())


    @tree.command(name="warn", description="⚠️ Avisa um membro")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(interaction: discord.Interaction, membro: discord.Member, motivo: str):
        total = add_warn(interaction.guild.id, membro.id, motivo, interaction.user)
        await interaction.response.send_message(f"⚠️ **{membro}** recebeu aviso #{total}.", ephemeral=True)
        await log_mod_action(interaction.guild, f"Warn #{total}", membro, interaction.user, motivo, discord.Color.orange())
        if total >= WARNS_BAN:
            await membro.ban(reason=f"Auto-ban: {total} warns")
            await log_mod_action(interaction.guild, "Auto-Ban", membro, interaction.guild.me, f"{total} warns acumulados")
        elif total >= WARNS_MUTE:
            until = discord.utils.utcnow() + datetime.timedelta(hours=1)
            await membro.timeout(until, reason=f"Auto-mute: {total} warns")
            await log_mod_action(interaction.guild, "Auto-Mute", membro, interaction.guild.me, f"{total} warns acumulados")


    @tree.command(name="warnings", description="📋 Avisos de um membro")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warnings_cmd(interaction: discord.Interaction, membro: discord.Member):
        ws = get_warns(interaction.guild.id, membro.id)
        if not ws:
            await interaction.response.send_message(f"✅ **{membro}** sem avisos.", ephemeral=True); return
        desc = "\n".join([f"`{n+1}.` {w['reason']}" for n, w in enumerate(ws)])
        await interaction.response.send_message(embed=discord.Embed(
            title=f"⚠️ Avisos de {membro.display_name}",
            description=desc, color=discord.Color.orange()
        ), ephemeral=True)


    @tree.command(name="clear", description="🧹 Apaga mensagens")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(interaction: discord.Interaction, quantidade: int = 10):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"🧹 {len(deleted)} mensagens apagadas.", ephemeral=True)


    @tree.command(name="historico", description="📜 Histórico de um membro")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def historico(interaction: discord.Interaction, membro: discord.Member):
        from config import get_xp
        data = get_xp(interaction.guild.id, membro.id)
        ws   = get_warns(interaction.guild.id, membro.id)
        embed = discord.Embed(
            title=f"📜 Histórico de {membro.display_name}",
            description=(
                f"**Nível:** {data.get('level',1)}\n"
                f"**Mensagens:** {data.get('messages',0)}\n"
                f"**Avisos:** {len(ws)}\n"
                f"**Entrou:** {discord.utils.format_dt(membro.joined_at,'D') if membro.joined_at else 'N/A'}"
            ),
            color=0xFF6B9D
        )
        embed.set_thumbnail(url=membro.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)