import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import yt_dlp
from config import *

# --- Variáveis Globais de Estado ---
music_queues  = {}  # {guild_id: [(url, title), ...]}
music_current = {}  # {guild_id: title}
music_repeat  = {}  # {guild_id: bool}
music_current_url = {}  # {guild_id: url}
playlists = {} # {user_id: {nome_playlist: [query, ...]}}

# --- Configurações do yt-dlp e FFmpeg ---
# SOLUÇÃO 1: Fingindo ser um celular/TV para burlar o bloqueio de bot
YDL_OPTS_YOUTUBE = {
    'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch1',
    'noplaylist': True,
    'socket_timeout': 10,
    'extractor_args': {
        'youtube': {
            'client': ['android', 'ios', 'tv', 'web']
        }
    },
}

YDL_OPTS_SOUNDCLOUD = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch1',
    'noplaylist': True,
    'socket_timeout': 10,
}

FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

RANDOM_QUERIES = [
    "anime openings 2024", "lofi hip hop", "J-pop hits",
    "manga soundtrack", "webtoon ost", "K-pop hits 2024",
    "anime soundtrack epic", "vocaloid songs", "city pop japanese",
]


async def get_audio(query: str):
    """Tenta YouTube primeiro, cai para SoundCloud se bloqueado."""
    loop = asyncio.get_event_loop()

    # Tentativa 1 — YouTube
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS_YOUTUBE) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
            if info:
                if 'entries' in info:
                    entries = [e for e in info['entries'] if e]
                    info = entries[0] if entries else None
                if info and info.get('url'):
                    return info['url'], info.get('title', 'Desconhecido'), '🎵 YouTube'
    except Exception as e:
        if 'Sign in' not in str(e) and 'bot' not in str(e).lower():
            raise

    # Tentativa 2 — SoundCloud
    sc_query = query if query.startswith("http") else f"scsearch1:{query.replace('ytsearch1:','')}"
    with yt_dlp.YoutubeDL(YDL_OPTS_SOUNDCLOUD) as ydl:
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(sc_query, download=False))
        if 'entries' in info:
            entries = [e for e in info['entries'] if e]
            info = entries[0] if entries else None
        if not info:
            raise ValueError("Nenhum resultado encontrado.")
        return info.get('url'), info.get('title', 'Desconhecido'), '☁️ SoundCloud'


async def get_playlist(url: str):
    loop = asyncio.get_event_loop()
    opts = {**YDL_OPTS_YOUTUBE, 'noplaylist': False, 'extract_flat': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        if 'entries' in info:
            return [(e.get('url', e.get('id')), e.get('title', 'Desconhecido')) for e in info['entries'] if e]
        return [(info.get('url'), info.get('title', 'Desconhecido'))]


async def play_next(guild: discord.Guild, bot):
    vc  = guild.voice_client
    gid = guild.id
    if not vc:
        return

    # Repeat mode
    if music_repeat.get(gid) and music_current_url.get(gid):
        url   = music_current_url[gid]
        title = music_current.get(gid, "?")
    elif music_queues.get(gid):
        url, title = music_queues[gid].pop(0)
        music_current[gid]     = title
        music_current_url[gid] = url
    else:
        music_current.pop(gid, None)
        music_current_url.pop(gid, None)
        await vc.disconnect(force=True)
        return

    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTS)
    source = discord.PCMVolumeTransformer(source, volume=0.5)
    vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild, bot), bot.loop))


def music_only():
    async def predicate(interaction: discord.Interaction):
        ch = discord.utils.get(interaction.guild.channels, name=MUSIC_CHANNEL)
        if ch and interaction.channel.id != ch.id:
            await interaction.response.send_message(f"❌ Use em {ch.mention}!", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


def setup_commands(tree: app_commands.CommandTree, bot):

    # --- Tratador de Erros Global da Tree ---
    @tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⏳ Calma aí! O comando está em tempo de recarga. Tente novamente em **{error.retry_after:.1f}s**.", ephemeral=True)
        else:
            print(f"Erro ignorado no comando {interaction.command.name}: {error}")


    @tree.command(name="play", description="🎵 Toca uma música (YouTube/Spotify/link)")
    @music_only()
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def play(interaction: discord.Interaction, musica: str):
        await interaction.response.defer()
        if not interaction.user.voice:
            await interaction.followup.send("❌ Entre em um canal de voz primeiro!", ephemeral=True)
            return
        vc  = interaction.guild.voice_client or await interaction.user.voice.channel.connect()
        gid = interaction.guild.id
        if gid not in music_queues: music_queues[gid] = []

        try:
            # Detectar se é playlist
            if "playlist" in musica.lower() or "list=" in musica:
                tracks = await get_playlist(musica)
                # Adiciona limite de 50 para evitar travamentos
                music_queues[gid].extend(tracks[:50]) 
                embed = discord.Embed(description=f"📋 **{len(tracks[:50])} músicas** adicionadas da playlist!", color=0xFF6B9D)
                await interaction.followup.send(embed=embed)
                if not vc.is_playing():
                    await play_next(interaction.guild, bot)
                return
            url, title, source = await get_audio(musica)
        except Exception as e:
            await interaction.followup.send(f"❌ Não encontrei: `{e}`", ephemeral=True)
            return

        if vc.is_playing() or vc.is_paused():
            music_queues[gid].append((url, title))
            embed = discord.Embed(description=f"📋 **{title}** adicionada à fila