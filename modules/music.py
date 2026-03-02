import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import wavelink
from config import *

# ── Playlists salvas em memória ────────────────────────────────────────────────
playlists = {}  # {user_id: {nome: [query, ...]}}

RANDOM_QUERIES = [
    "anime openings 2024", "lofi hip hop", "J-pop hits",
    "manga soundtrack", "webtoon ost", "K-pop hits 2024",
    "anime soundtrack epic", "vocaloid songs", "city pop japanese",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def music_only():
    """Restringe o comando ao canal de música configurado."""
    async def predicate(interaction: discord.Interaction):
        ch = discord.utils.get(interaction.guild.channels, name=MUSIC_CHANNEL)
        if ch and interaction.channel.id != ch.id:
            await interaction.response.send_message(
                f"❌ Use em {ch.mention}!", ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)


async def get_player(interaction: discord.Interaction) -> wavelink.Player | None:
    """Retorna o Player do guild, conectando ao canal de voz se necessário."""
    if not interaction.user.voice:
        await interaction.followup.send("❌ Entre em um canal de voz primeiro!", ephemeral=True)
        return None

    vc: wavelink.Player = interaction.guild.voice_client  # type: ignore

    if vc is None:
        vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        vc.autoplay = wavelink.AutoPlayMode.disabled

    return vc


async def search_track(query: str) -> wavelink.Playable | None:
    """
    Busca uma faixa no YouTube (via LavaSrc/youtube-source plugin).
    Cai para SoundCloud se não encontrar resultado no YouTube.
    """
    # Tenta YouTube
    try:
        if query.startswith("http"):
            tracks = await wavelink.Playable.search(query)
        else:
            tracks = await wavelink.Playable.search(f"ytsearch:{query}")

        if tracks:
            return tracks[0] if isinstance(tracks, list) else tracks
    except Exception:
        pass

    # Fallback: SoundCloud
    try:
        sc_query = query if query.startswith("http") else f"scsearch:{query}"
        tracks = await wavelink.Playable.search(sc_query)
        if tracks:
            return tracks[0] if isinstance(tracks, list) else tracks
    except Exception:
        pass

    return None


async def search_playlist(url: str) -> list[wavelink.Playable]:
    """Busca todas as faixas de uma playlist."""
    result = await wavelink.Playable.search(url)
    if isinstance(result, wavelink.Playlist):
        return list(result.tracks)
    elif isinstance(result, list):
        return result
    return []


# ── Setup de Comandos ──────────────────────────────────────────────────────────

def setup_commands(tree: app_commands.CommandTree, bot):

    # ── Conectar ao Lavalink ao iniciar ─────────────────────────────────────
    @bot.event
    async def on_ready_lavalink():
        pass  # conexão feita em bot.py via setup_hook

    # ── Erro global ─────────────────────────────────────────────────────────
    @tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"⏳ Aguarde **{error.retry_after:.1f}s** antes de usar novamente.",
                    ephemeral=True,
                )
        else:
            cmd = interaction.command.name if interaction.command else "?"
            print(f"Erro no comando /{cmd}: {error}")

    # ── /play ────────────────────────────────────────────────────────────────
    @tree.command(name="play", description="🎵 Toca uma música (YouTube/SoundCloud/link)")
    @music_only()
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def play(interaction: discord.Interaction, musica: str):
        await interaction.response.defer()

        vc = await get_player(interaction)
        if vc is None:
            return

        # ── Playlist ─────────────────────────────────────────────────────
        if "playlist" in musica.lower() or "list=" in musica or "album" in musica.lower():
            tracks = await search_playlist(musica)
            if not tracks:
                await interaction.followup.send("❌ Playlist não encontrada.", ephemeral=True)
                return
            limited = tracks[:50]
            for t in limited:
                await vc.queue.put_wait(t)
            embed = discord.Embed(
                description=f"📋 **{len(limited)} músicas** adicionadas da playlist!",
                color=0xFF6B9D,
            )
            if not vc.playing:
                await vc.play(vc.queue.get())
            await interaction.followup.send(embed=embed)
            return

        # ── Faixa única ───────────────────────────────────────────────────
        track = await search_track(musica)
        if not track:
            await interaction.followup.send("❌ Não encontrei essa música.", ephemeral=True)
            return

        source_icon = "☁️ SoundCloud" if "soundcloud" in (track.uri or "") else "🎵 YouTube"

        if vc.playing or not vc.queue.is_empty:
            await vc.queue.put_wait(track)
            embed = discord.Embed(
                description=f"📋 **{track.title}** adicionada à fila! (#{vc.queue.count}) {source_icon}",
                color=0xFF6B9D,
            )
        else:
            await vc.play(track)
            embed = discord.Embed(
                description=f"▶️ Tocando: **{track.title}** {source_icon}",
                color=0xFF6B9D,
            )
        await interaction.followup.send(embed=embed)

    # ── /playaleatorio ───────────────────────────────────────────────────────
    @tree.command(name="playaleatorio", description="🎲 Toca uma música aleatória de anime/webtoon")
    @music_only()
    async def play_random(interaction: discord.Interaction):
        await interaction.response.defer()

        vc = await get_player(interaction)
        if vc is None:
            return

        query = random.choice(RANDOM_QUERIES)
        track = await search_track(query)
        if not track:
            await interaction.followup.send("❌ Erro ao buscar música aleatória.", ephemeral=True)
            return

        if vc.playing or not vc.queue.is_empty:
            await vc.queue.put_wait(track)
            embed = discord.Embed(
                description=f"🎲 Surpresa! **{track.title}** na fila!",
                color=0xFF6B9D,
            )
        else:
            await vc.play(track)
            embed = discord.Embed(
                description=f"🎲 Tocando aleatório: **{track.title}**",
                color=0xFF6B9D,
            )
        await interaction.followup.send(embed=embed)

    # ── /skip ────────────────────────────────────────────────────────────────
    @tree.command(name="skip", description="⏭️ Pula para a próxima música")
    @music_only()
    async def skip(interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if vc and (vc.playing or vc.paused):
            await vc.skip(force=True)
            await interaction.response.send_message("⏭️ Pulando!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

    # ── /pause ───────────────────────────────────────────────────────────────
    @tree.command(name="pause", description="⏸️ Pausa a música")
    @music_only()
    async def pause(interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if vc and vc.playing:
            await vc.pause(True)
            await interaction.response.send_message("⏸️ Pausado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

    # ── /resume ──────────────────────────────────────────────────────────────
    @tree.command(name="resume", description="▶️ Retoma a música")
    @music_only()
    async def resume(interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if vc and vc.paused:
            await vc.pause(False)
            await interaction.response.send_message("▶️ Retomado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada pausado.", ephemeral=True)

    # ── /stop ────────────────────────────────────────────────────────────────
    @tree.command(name="stop", description="⏹️ Para e desconecta")
    @music_only()
    async def stop(interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if vc:
            vc.queue.clear()
            await vc.stop()
            await vc.disconnect(force=True)
        await interaction.response.send_message("⏹️ Parado.", ephemeral=True)

    # ── /queue ───────────────────────────────────────────────────────────────
    @tree.command(name="queue", description="📋 Fila de músicas")
    @music_only()
    async def queue_cmd(interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        current = vc.current.title if vc and vc.current else "Nenhuma"
        repeat_status = "🔁 ON" if (vc and vc.queue.mode == wavelink.QueueMode.loop) else "🔁 OFF"
        fila = list(vc.queue) if vc else []

        desc = f"▶️ **Tocando:** {current} | {repeat_status}\n\n"
        if fila:
            desc += "\n".join([f"`{n+1}.` {t.title}" for n, t in enumerate(fila[:10])])
            if len(fila) > 10:
                desc += f"\n*...e mais {len(fila)-10} músicas*"
        else:
            desc += "*Fila vazia*"

        await interaction.response.send_message(
            embed=discord.Embed(title="🎵 Fila", description=desc, color=0xFF6B9D)
        )

    # ── /nowplaying ──────────────────────────────────────────────────────────
    @tree.command(name="nowplaying", description="🎵 Música tocando agora")
    @music_only()
    async def nowplaying(interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if vc and vc.current:
            track = vc.current
            dur = f"{track.length // 60000}:{(track.length // 1000 % 60):02d}"
            pos_ms = vc.position
            pos = f"{pos_ms // 60000}:{(pos_ms // 1000 % 60):02d}"
            desc = f"▶️ **{track.title}**\n⏱️ `{pos} / {dur}`"
            if track.uri:
                desc += f"\n🔗 [Link]({track.uri})"
        else:
            desc = "❌ Nada tocando."
        await interaction.response.send_message(
            embed=discord.Embed(description=desc, color=0xFF6B9D)
        )

    # ── /volume ──────────────────────────────────────────────────────────────
    @tree.command(name="volume", description="🔊 Ajusta volume (0-100)")
    @music_only()
    async def volume(interaction: discord.Interaction, valor: int):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if vc:
            vol = max(0, min(valor, 100))
            await vc.set_volume(vol)
            await interaction.response.send_message(f"🔊 Volume: **{vol}%**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

    # ── /shuffle ─────────────────────────────────────────────────────────────
    @tree.command(name="shuffle", description="🔀 Embaralha a fila de músicas")
    @music_only()
    async def shuffle(interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if vc and not vc.queue.is_empty:
            vc.queue.shuffle()
            await interaction.response.send_message(
                f"🔀 Fila embaralhada! ({vc.queue.count} músicas)", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Fila vazia.", ephemeral=True)

    # ── /repeat ──────────────────────────────────────────────────────────────
    @tree.command(name="repeat", description="🔁 Ativa/desativa repetição da música atual")
    @music_only()
    async def repeat(interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not vc:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)
            return
        if vc.queue.mode == wavelink.QueueMode.loop:
            vc.queue.mode = wavelink.QueueMode.normal
            status = "**desativada**"
        else:
            vc.queue.mode = wavelink.QueueMode.loop
            status = "**ativada** 🔁"
        await interaction.response.send_message(f"Repetição {status}", ephemeral=True)

    # ── /playlist ────────────────────────────────────────────────────────────
    @tree.command(name="playlist", description="📻 Gerencia suas playlists salvas")
    @music_only()
    async def playlist_cmd(
        interaction: discord.Interaction,
        acao: str,
        nome: str,
        musica: str = None,
    ):
        uid = str(interaction.user.id)
        if uid not in playlists:
            playlists[uid] = {}

        if acao == "criar":
            playlists[uid][nome] = []
            await interaction.response.send_message(f"✅ Playlist **{nome}** criada!", ephemeral=True)

        elif acao == "adicionar" and musica:
            if nome not in playlists[uid]:
                await interaction.response.send_message("❌ Playlist não encontrada.", ephemeral=True)
                return
            playlists[uid][nome].append(musica)
            await interaction.response.send_message(
                f"✅ **{musica}** adicionada à **{nome}**!", ephemeral=True
            )

        elif acao == "tocar":
            if nome not in playlists[uid] or not playlists[uid][nome]:
                await interaction.response.send_message(
                    "❌ Playlist vazia ou não encontrada.", ephemeral=True
                )
                return
            await interaction.response.defer()
            vc = await get_player(interaction)
            if vc is None:
                return
            count = 0
            for q in playlists[uid][nome]:
                track = await search_track(q)
                if track:
                    await vc.queue.put_wait(track)
                    count += 1
            if not vc.playing and not vc.queue.is_empty:
                await vc.play(vc.queue.get())
            await interaction.followup.send(
                f"▶️ Tocando playlist **{nome}** ({count} músicas)!"
            )

        elif acao == "ver":
            pls = playlists.get(uid, {})
            if nome in pls:
                desc = "\n".join([f"`{i+1}.` {m}" for i, m in enumerate(pls[nome])]) or "*Vazia*"
                await interaction.response.send_message(
                    embed=discord.Embed(title=f"📻 {nome}", description=desc, color=0xFF6B9D),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message("❌ Playlist não encontrada.", ephemeral=True)

        else:
            await interaction.response.send_message(
                "❌ Ações disponíveis: `criar`, `adicionar`, `tocar`, `ver`", ephemeral=True
            )