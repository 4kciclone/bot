import discord
from discord import app_commands
import datetime
from config import *


def setup_commands(tree: app_commands.CommandTree, bot):

    @tree.command(name="perfil", description="🎨 Veja o perfil completo de um membro")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def perfil(interaction: discord.Interaction, membro: discord.Member = None):
        membro = membro or interaction.user
        data   = get_xp(interaction.guild.id, membro.id)
        level  = data.get("level", 1)
        xp     = data.get("xp", 0)
        needed = xp_needed(level)
        msgs   = data.get("messages", 0)
        total  = data.get("total_xp", 0)
        warns  = len(get_warns(interaction.guild.id, membro.id))

        from modules.xp import get_streak
        streak = get_streak(interaction.guild.id, membro.id)["streak"]

        # Barra de XP
        filled = int((xp / needed) * 20) if needed > 0 else 0
        bar    = "█" * filled + "░" * (20 - filled)

        # Tempo no servidor
        if membro.joined_at:
            delta = datetime.datetime.utcnow().replace(tzinfo=None) - membro.joined_at.replace(tzinfo=None)
            days  = delta.days
            time_str = f"{days} dias"
        else:
            time_str = "N/A"

        # Cargos especiais
        special_roles = [r.name for r in membro.roles if r.name not in ["@everyone", "🆕 Novato"] and not r.is_default()]
        roles_str = " ".join(special_roles[:5]) if special_roles else "Nenhum"

        # Badge de nível
        if level >= 30: badge = "🔥 Lenda"
        elif level >= 15: badge = "💎 Veterano"
        elif level >= 5: badge = "⭐ Ativo"
        else: badge = "🌱 Iniciante"

        embed = discord.Embed(
            title=f"👤 Perfil de {membro.display_name}",
            color=0xFF6B9D,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(
            name="📊 Progresso",
            value=(
                f"**Nível:** {level} {badge}\n"
                f"**XP:** {xp}/{needed}\n"
                f"`{bar}` {int((xp/needed)*100) if needed > 0 else 0}%"
            ),
            inline=False
        )
        embed.add_field(
            name="📈 Estatísticas",
            value=(
                f"💬 Mensagens: **{msgs}**\n"
                f"🏆 XP Total: **{total}**\n"
                f"🔥 Streak: **{streak} dias**\n"
                f"⚠️ Warns: **{warns}**"
            ),
            inline=True
        )
        embed.add_field(
            name="🏷️ Info",
            value=(
                f"📅 No servidor há: **{time_str}**\n"
                f"🎭 Cargos: {roles_str}"
            ),
            inline=True
        )
        embed.set_footer(text="Gato Comics 🐱")
        await interaction.response.send_message(embed=embed)