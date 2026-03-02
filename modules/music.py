import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import yt_dlp
from config import *

music_queues  = {}  # {guild_id: [(url, title), ...]}
music_current = {}  # {guild_id: title}
music_repeat  = {}  # {guild_id: bool}
music_current_url = {}  # {guild_id: url}

YDL_OPTS_YOUTUBE = {
    'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch1',
    'noplaylist': True,
    'socket_timeout': 10,
    'extractor_args': {'youtube': {'player_client': ['web']}},
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
    opts = {**YDL_OPTS, 'noplaylist': False, 'extract_flat': True}
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
        await vc.disconnect()
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
                music_queues[gid].extend(tracks)
                embed = discord.Embed(description=f"📋 **{len(tracks)} músicas** adicionadas da playlist!", color=0xFF6B9D)
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
            embed = discord.Embed(description=f"📋 **{title}** adicionada à fila! (#{len(music_queues[gid])}) {source}", color=0xFF6B9D)
        else:
            music_queues[gid].insert(0, (url, title))
            await play_next(interaction.guild, bot)
            embed = discord.Embed(description=f"▶️ Tocando: **{title}** {source}", color=0xFF6B9D)
        await interaction.followup.send(embed=embed)

    @tree.command(name="playaleatorio", description="🎲 Toca uma música aleatória de anime/webtoon")
    @music_only()
    async def play_random(interaction: discord.Interaction):
        await interaction.response.defer()
        if not interaction.user.voice:
            await interaction.followup.send("❌ Entre em um canal de voz primeiro!", ephemeral=True)
            return
        vc  = interaction.guild.voice_client or await interaction.user.voice.channel.connect()
        gid = interaction.guild.id
        if gid not in music_queues: music_queues[gid] = []

        try:
            url, title, source = await get_audio(query)
        except:
            await interaction.followup.send("❌ Erro ao buscar música aleatória.", ephemeral=True)
            return

        if vc.is_playing():
            music_queues[gid].append((url, title))
            embed = discord.Embed(description=f"🎲 Surpresa! **{title}** na fila! {source}", color=0xFF6B9D)
        else:
            music_queues[gid].insert(0, (url, title))
            await play_next(interaction.guild, bot)
            embed = discord.Embed(description=f"🎲 Tocando aleatório: **{title}** {source}", color=0xFF6B9D)
        await interaction.followup.send(embed=embed)

    @tree.command(name="skip", description="⏭️ Pula para a próxima música")
    @music_only()
    async def skip(interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Pulando!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

    @tree.command(name="pause", description="⏸️ Pausa a música")
    @music_only()
    async def pause(interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Pausado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

    @tree.command(name="resume", description="▶️ Retoma a música")
    @music_only()
    async def resume(interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Retomado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada pausado.", ephemeral=True)

    @tree.command(name="stop", description="⏹️ Para e desconecta")
    @music_only()
    async def stop(interaction: discord.Interaction):
        gid = interaction.guild.id
        music_queues.pop(gid, None)
        music_current.pop(gid, None)
        music_repeat.pop(gid, None)
        vc = interaction.guild.voice_client
        if vc: await vc.disconnect()
        await interaction.response.send_message("⏹️ Parado.", ephemeral=True)

    @tree.command(name="queue", description="📋 Fila de músicas")
    @music_only()
    async def queue_cmd(interaction: discord.Interaction):
        gid  = interaction.guild.id
        cur  = music_current.get(gid, "Nenhuma")
        rep  = "🔁 ON" if music_repeat.get(gid) else "🔁 OFF"
        fila = music_queues.get(gid, [])
        desc = f"▶️ **Tocando:** {cur} | {rep}\n\n"
        desc += "\n".join([f"`{n+1}.` {t}" for n, (_, t) in enumerate(fila[:10])]) if fila else "*Fila vazia*"
        if len(fila) > 10:
            desc += f"\n*...e mais {len(fila)-10} músicas*"
        await interaction.response.send_message(embed=discord.Embed(title="🎵 Fila", description=desc, color=0xFF6B9D))

    @tree.command(name="nowplaying", description="🎵 Música tocando agora")
    @music_only()
    async def nowplaying(interaction: discord.Interaction):
        cur = music_current.get(interaction.guild.id)
        desc = f"▶️ **{cur}**" if cur else "❌ Nada tocando."
        await interaction.response.send_message(embed=discord.Embed(description=desc, color=0xFF6B9D))

    @tree.command(name="volume", description="🔊 Ajusta volume (0-100)")
    @music_only()
    async def volume(interaction: discord.Interaction, valor: int):
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = max(0, min(valor, 100)) / 100
            await interaction.response.send_message(f"🔊 Volume: **{valor}%**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

    @tree.command(name="shuffle", description="🔀 Embaralha a fila de músicas")
    @music_only()
    async def shuffle(interaction: discord.Interaction):
        gid  = interaction.guild.id
        fila = music_queues.get(gid, [])
        if not fila:
            await interaction.response.send_message("❌ Fila vazia.", ephemeral=True)
            return
        random.shuffle(fila)
        music_queues[gid] = fila
        await interaction.response.send_message(f"🔀 Fila embaralhada! ({len(fila)} músicas)", ephemeral=True)

    @tree.command(name="repeat", description="🔁 Ativa/desativa repetição da música atual")
    @music_only()
    async def repeat(interaction: discord.Interaction):
        gid = interaction.guild.id
        music_repeat[gid] = not music_repeat.get(gid, False)
        status = "**ativada** 🔁" if music_repeat[gid] else "**desativada**"
        await interaction.response.send_message(f"Repetição {status}", ephemeral=True)

    @tree.command(name="playlist", description="📻 Gerencia suas playlists salvas")
    @music_only()
    async def playlist_cmd(interaction: discord.Interaction, acao: str, nome: str, musica: str = None):
        uid = str(interaction.user.id)
        if uid not in playlists: playlists[uid] = {}

        if acao == "criar":
            playlists[uid][nome] = []
            await interaction.response.send_message(f"✅ Playlist **{nome}** criada!", ephemeral=True)
        elif acao == "adicionar" and musica:
            if nome not in playlists[uid]:
                await interaction.response.send_message("❌ Playlist não encontrada.", ephemeral=True); return
            playlists[uid][nome].append(musica)
            await interaction.response.send_message(f"✅ **{musica}** adicionada à **{nome}**!", ephemeral=True)
        elif acao == "tocar":
            if nome not in playlists[uid] or not playlists[uid][nome]:
                await interaction.response.send_message("❌ Playlist vazia ou não encontrada.", ephemeral=True); return
            await interaction.response.defer()
            if not interaction.user.voice:
                await interaction.followup.send("❌ Entre em um canal de voz!", ephemeral=True); return
            vc  = interaction.guild.voice_client or await interaction.user.voice.channel.connect()
            gid = interaction.guild.id
            if gid not in music_queues: music_queues[gid] = []
            for q in playlists[uid][nome]:
                try:
                    url, title = await get_audio(q)
                    music_queues[gid].append((url, title))
                except: pass
            if not vc.is_playing():
                await play_next(interaction.guild, bot)
            await interaction.followup.send(f"▶️ Tocando playlist **{nome}** ({len(playlists[uid][nome])} músicas)!")
        elif acao == "ver":
            pls = playlists.get(uid, {})
            if nome in pls:
                desc = "\n".join([f"`{i+1}.` {m}" for i, m in enumerate(pls[nome])]) or "*Vazia*"
                await interaction.response.send_message(embed=discord.Embed(title=f"📻 {nome}", description=desc, color=0xFF6B9D), ephemeral=True)
            else:
                await interaction.response.send_message("❌ Playlist não encontrada.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Ações: `criar`, `adicionar`, `tocar`, `ver`", ephemeral=True)