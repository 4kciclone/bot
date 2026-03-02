import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
from config import TOKEN, WELCOME_CHANNEL, CONQUEST_CHANNEL, STATS_CATEGORY

# ─────────────────────────────────────────
#  Inicialização
# ─────────────────────────────────────────
intents = discord.Intents.all()
bot     = commands.Bot(command_prefix="g!", intents=intents)
tree    = bot.tree


# ─────────────────────────────────────────
#  Carregar módulos
# ─────────────────────────────────────────
from modules.setup      import setup_commands       as setup_setup
from modules.tickets    import setup_commands       as setup_tickets, TicketCategoryView, TicketCloseView
from modules.music      import setup_commands       as setup_music
from modules.xp         import setup_commands       as setup_xp
from modules.moderation import setup_commands       as setup_moderation, on_message_ai
from modules.games      import setup_commands       as setup_games
from modules.ai         import setup_commands       as setup_ai
from modules.events     import setup_commands       as setup_events
from modules.profile    import setup_commands       as setup_profile

setup_setup(tree, bot)
setup_tickets(tree, bot)
setup_music(tree, bot)
setup_xp(tree, bot)
setup_moderation(tree, bot)
setup_games(tree, bot)
setup_ai(tree, bot)
setup_events(tree, bot)
setup_profile(tree, bot)


# ─────────────────────────────────────────
#  Eventos globais
# ─────────────────────────────────────────

@bot.event
async def on_ready():
    # Views persistentes (sobrevivem ao restart)
    bot.add_view(TicketCategoryView())
    bot.add_view(TicketCloseView())

    await tree.sync()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="🐱 Gato Comics")
    )

    # Iniciar tasks agendadas
    if hasattr(bot, '_update_stats') and not bot._update_stats.is_running():
        bot._update_stats.start()
    if hasattr(bot, '_check_scheduled') and not bot._check_scheduled.is_running():
        bot._check_scheduled.start()
    if hasattr(bot, '_weekly_ranking') and not bot._weekly_ranking.is_running():
        bot._weekly_ranking.start()

    print(f"✅ {bot.user} online! | {len(bot.guilds)} servidor(es)")
    print(f"📋 Comandos sincronizados!")


@bot.event
async def on_member_join(member: discord.Member):
    guild  = member.guild
    novato = discord.utils.get(guild.roles, name="🆕 Novato")
    if novato:
        await member.add_roles(novato)

    # Atualizar estatísticas
    for vc in guild.voice_channels:
        if vc.name.startswith("👥 Membros:"):
            try: await vc.edit(name=f"👥 Membros: {guild.member_count}")
            except: pass

    ch = discord.utils.get(guild.channels, name=WELCOME_CHANNEL)
    if ch:
        embed = discord.Embed(
            title=f"🐱 Seja bem-vindo, {member.display_name}!",
            description=(
                f"Que ótimo ter você aqui, {member.mention}! 🎉\n\n"
                "Complete o onboarding para ter acesso completo ao servidor.\n"
                "Use `/perfil` para ver seu progresso e `/missoes` para missões diárias!"
            ),
            color=0xFF6B9D
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)


@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild

    # Atualizar estatísticas
    for vc in guild.voice_channels:
        if vc.name.startswith("👥 Membros:"):
            try: await vc.edit(name=f"👥 Membros: {guild.member_count}")
            except: pass

    ch = discord.utils.get(guild.channels, name=WELCOME_CHANNEL)
    if ch:
        embed = discord.Embed(
            description=f"👋 **{member.display_name}** saiu do servidor. Até mais!",
            color=discord.Color.light_grey()
        )
        await ch.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Passar para módulo de XP (já registrado via setup_xp)
    # Passar para moderação IA
    await on_message_ai(message)

    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    # Verificar votos de arte
    from modules.games import art_votes
    from config import get_xp, set_xp
    if reaction.message.id in art_votes and str(reaction.emoji) == "❤️":
        art_votes[reaction.message.id]["votes"] = art_votes[reaction.message.id].get("votes", 0) + 1


@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ Aguarde **{error.retry_after:.0f}s** para usar este comando novamente!",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Você não tem permissão para isso!", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        pass  # Já tratado nos checks individuais
    else:
        await interaction.response.send_message(f"❌ Erro: {str(error)[:100]}", ephemeral=True)
        print(f"[ERRO] {error}")


# ─────────────────────────────────────────
#  Iniciar bot
# ─────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        print("❌ TOKEN não encontrado no .env!")
        exit(1)
    bot.run(TOKEN)