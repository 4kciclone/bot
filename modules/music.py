import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import json
import urllib.request
import urllib.parse
from config import *

# ── Playlists salvas em memória ────────────────────────────────────────────────
playlists = {}  # {user_id: {nome: [query, ...]}}

RANDOM_QUERIES = [
    "anime openings 2024", "lofi hip hop", "J-pop hits",
    "manga soundtrack", "webtoon ost", "K-pop hits 2024",
    "anime soundtrack epic", "vocaloid songs", "city pop japanese",
]

# ── Estado do player por guild ─────────────────────────────────────────────────
guild_queues = {}  # {guild_id: {"queue": [], "current": None, "repeat": False, "volume": 0.5}}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -b:a 128k",
}

COOKIES_YT = "/root/gatocomics-bot/cookies.txt"
COOKIES_DZ = "/root/gatocomics-bot/deezer_cookies.txt"


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


def get_guild_data(guild_id):
    """Retorna ou cria dados do guild."""
    if guild_id not in guild_queues:
        guild_queues[guild_id] = {
            "queue": [],
            "current": None,
            "repeat": False,
            "volume": 0.5,
        }
    return guild_queues[guild_id]


async def search_deezer_api(query: str) -> dict | None:
    """Busca na API pública do Deezer. Retorna {id, title, artist, duration}."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.deezer.com/search?q={encoded}&limit=5"

        def _fetch():
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())

        data = await asyncio.get_event_loop().run_in_executor(None, _fetch)
        tracks = data.get("data", [])
        if not tracks:
            return None

        t = tracks[0]
        return {
            "id": t["id"],
            "title": f"{t['artist']['name']} - {t['title']}",
            "duration": t.get("duration", 0),
            "deezer_url": t.get("link", f"https://www.deezer.com/track/{t['id']}"),
        }
    except Exception as e:
        print(f"[DEEZER] ⚠️ API erro: {e}", flush=True)
        return None


async def extract_audio(url: str, cookies: str = None) -> dict | None:
    """Usa yt-dlp para extrair URL de áudio de qualquer fonte."""
    try:
        cmd = ["yt-dlp", "--no-warnings", "-q", "-j", "--no-playlist"]
        if cookies:
            cmd += ["--cookies", cookies]
        cmd.append(url)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            err = stderr.decode()[:200]
            print(f"[YTDLP] ⚠️ erro: {err}", flush=True)
            return None

        data = json.loads(stdout.decode())
        audio_url = data.get("url")
        if not audio_url:
            formats = data.get("formats", [])
            audio_formats = [f for f in formats if f.get("acodec") != "none" and f.get("url")]
            if audio_formats:
                audio_url = audio_formats[-1]["url"]

        if not audio_url:
            return None

        return {
            "title": data.get("title", "Desconhecido"),
            "url": audio_url,
            "duration": data.get("duration", 0),
            "webpage_url": data.get("webpage_url", ""),
        }
    except asyncio.TimeoutError:
        print(f"[YTDLP] ❌ Timeout", flush=True)
        return None
    except Exception as e:
        print(f"[YTDLP] ❌ Erro: {e}", flush=True)
        return None


async def search_track(query: str) -> dict | None:
    """Busca e extrai áudio. Prioridade: Deezer → YouTube."""
    # URL direta
    if query.startswith("http"):
        cookies = COOKIES_DZ if "deezer" in query else COOKIES_YT
        result = await extract_audio(query, cookies)
        if result:
            print(f"[MÚSICA] ✅ URL: {result['title']}", flush=True)
            return result
        return None

    # 1. Buscar no Deezer
    dz = await search_deezer_api(query)
    if dz:
        print(f"[DEEZER] 🔍 Encontrado: {dz['title']}", flush=True)
        result = await extract_audio(dz["deezer_url"], COOKIES_DZ)
        if result:
            print(f"[MÚSICA] ✅ Deezer: {result['title']}", flush=True)
            return result
        print(f"[DEEZER] ⚠️ Extração falhou, tentando YouTube...", flush=True)

    # 2. Fallback: YouTube com cookies
    result = await extract_audio(f"ytsearch:{query}", COOKIES_YT)
    if result:
        print(f"[MÚSICA] ✅ YouTube: {result['title']}", flush=True)
        return result

    print(f"[MÚSICA] ❌ Não encontrado: {query}", flush=True)
    return None


async def play_next(guild: discord.Guild):
    """Toca a próxima música da fila."""
    data = get_guild_data(guild.id)
    vc: discord.VoiceClient = guild.voice_client

    if not vc or not vc.is_connected():
        return

    # Repeat mode
    if data["repeat"] and data["current"]:
        track = data["current"]
    elif data["queue"]:
        track = data["queue"].pop(0)
        data["current"] = track
    else:
        data["current"] = None
        print("[FILA] Fila vazia, parando.", flush=True)
        await asyncio.sleep(120)  # espera 2 min antes de desconectar
        if guild.voice_client and not guild.voice_client.is_playing():
            await guild.voice_client.disconnect(force=True)
        return

    try:
        print(f"[FILA] ▶️ Tocando: {track['title']}", flush=True)
        source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTS)
        source = discord.PCMVolumeTransformer(source, volume=data["volume"])

        def after_play(error):
            if error:
                print(f"[FILA] ❌ Erro playback: {error}", flush=True)
            # Agendar próxima música
            asyncio.run_coroutine_threadsafe(play_next(guild), guild._state.loop)

        vc.play(source, after=after_play)
    except Exception as e:
        print(f"[FILA] ❌ Erro ao iniciar: {e}", flush=True)
        asyncio.run_coroutine_threadsafe(play_next(guild), guild._state.loop)


# ── Setup de Comandos ──────────────────────────────────────────────────────────

def setup_commands(tree: app_commands.CommandTree, bot):

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
    @tree.command(name="play", description="🎵 Toca uma música (YouTube/link)")
    @music_only()
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def play(interaction: discord.Interaction, musica: str):
        await interaction.response.defer()

        try:
            if not interaction.user.voice:
                await interaction.followup.send("❌ Entre em um canal de voz primeiro!", ephemeral=True)
                return

            vc: discord.VoiceClient = interaction.guild.voice_client
            if vc is None:
                vc = await interaction.user.voice.channel.connect(timeout=30.0, self_deaf=True)
            elif not vc.is_connected():
                try:
                    await vc.disconnect(force=True)
                except:
                    pass
                vc = await interaction.user.voice.channel.connect(timeout=30.0, self_deaf=True)

            data = get_guild_data(interaction.guild.id)

            # Buscar música
            track = await search_track(musica)
            if not track:
                await interaction.followup.send("❌ Não encontrei essa música.", ephemeral=True)
                return

            print(f"[MÚSICA] ✅ {track['title']}", flush=True)

            if vc.is_playing() or data["queue"]:
                data["queue"].append(track)
                embed = discord.Embed(
                    description=f"📋 **{track['title']}** adicionada à fila! (#{len(data['queue'])})",
                    color=0xFF6B9D,
                )
            else:
                data["current"] = track
                embed = discord.Embed(
                    description=f"▶️ Tocando: **{track['title']}** 🎵",
                    color=0xFF6B9D,
                )
                source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTS)
                source = discord.PCMVolumeTransformer(source, volume=data["volume"])

                def after_play(error):
                    if error:
                        print(f"[FILA] ❌ Erro: {error}", flush=True)
                    asyncio.run_coroutine_threadsafe(play_next(interaction.guild), bot.loop)

                vc.play(source, after=after_play)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[PLAY] ❌ ERRO: {e}", flush=True)
            try:
                await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
            except:
                pass

    # ── /playaleatorio ───────────────────────────────────────────────────────
    @tree.command(name="playaleatorio", description="🎲 Toca uma música aleatória de anime/webtoon")
    @music_only()
    async def play_random(interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            if not interaction.user.voice:
                await interaction.followup.send("❌ Entre em um canal de voz primeiro!", ephemeral=True)
                return

            vc: discord.VoiceClient = interaction.guild.voice_client
            if vc is None:
                vc = await interaction.user.voice.channel.connect(timeout=30.0, self_deaf=True)

            data = get_guild_data(interaction.guild.id)
            query = random.choice(RANDOM_QUERIES)
            track = await search_track(query)
            if not track:
                await interaction.followup.send("❌ Erro ao buscar música aleatória.", ephemeral=True)
                return

            if vc.is_playing() or data["queue"]:
                data["queue"].append(track)
                embed = discord.Embed(
                    description=f"🎲 Surpresa! **{track['title']}** na fila!",
                    color=0xFF6B9D,
                )
            else:
                data["current"] = track
                embed = discord.Embed(
                    description=f"🎲 Tocando aleatório: **{track['title']}**",
                    color=0xFF6B9D,
                )
                source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTS)
                source = discord.PCMVolumeTransformer(source, volume=data["volume"])

                def after_play(error):
                    if error:
                        print(f"[FILA] ❌ Erro: {error}", flush=True)
                    asyncio.run_coroutine_threadsafe(play_next(interaction.guild), bot.loop)

                vc.play(source, after=after_play)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            print(f"[PLAY] ❌ ERRO: {e}", flush=True)
            try:
                await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
            except:
                pass

    # ── /skip ────────────────────────────────────────────────────────────────
    @tree.command(name="skip", description="⏭️ Pula para a próxima música")
    @music_only()
    async def skip(interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()  # vai chamar after_play que toca a próxima
            await interaction.response.send_message("⏭️ Pulando!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

    # ── /pause ───────────────────────────────────────────────────────────────
    @tree.command(name="pause", description="⏸️ Pausa a música")
    @music_only()
    async def pause(interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Pausado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada tocando.", ephemeral=True)

    # ── /resume ──────────────────────────────────────────────────────────────
    @tree.command(name="resume", description="▶️ Retoma a música")
    @music_only()
    async def resume(interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Retomado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nada pausado.", ephemeral=True)

    # ── /stop ────────────────────────────────────────────────────────────────
    @tree.command(name="stop", description="⏹️ Para e desconecta")
    @music_only()
    async def stop(interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if vc:
            data = get_guild_data(interaction.guild.id)
            data["queue"].clear()
            data["current"] = None
            data["repeat"] = False
            vc.stop()
            await vc.disconnect(force=True)
        await interaction.response.send_message("⏹️ Parado.", ephemeral=True)

    # ── /queue ───────────────────────────────────────────────────────────────
    @tree.command(name="queue", description="📋 Fila de músicas")
    @music_only()
    async def queue_cmd(interaction: discord.Interaction):
        data = get_guild_data(interaction.guild.id)
        current = data["current"]["title"] if data["current"] else "Nenhuma"
        repeat_status = "🔁 ON" if data["repeat"] else "🔁 OFF"
        fila = data["queue"]

        desc = f"▶️ **Tocando:** {current} | {repeat_status}\n\n"
        if fila:
            desc += "\n".join([f"`{n+1}.` {t['title']}" for n, t in enumerate(fila[:10])])
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
        data = get_guild_data(interaction.guild.id)
        vc: discord.VoiceClient = interaction.guild.voice_client
        if data["current"] and vc and vc.is_playing():
            track = data["current"]
            dur_s = track.get("duration", 0)
            dur = f"{dur_s // 60}:{(dur_s % 60):02d}"
            desc = f"▶️ **{track['title']}**\n⏱️ Duração: `{dur}`"
            if track.get("webpage_url"):
                desc += f"\n🔗 [Link]({track['webpage_url']})"
        else:
            desc = "❌ Nada tocando."
        await interaction.response.send_message(
            embed=discord.Embed(description=desc, color=0xFF6B9D)
        )

    # ── /volume ──────────────────────────────────────────────────────────────
    @tree.command(name="volume", description="🔊 Ajusta volume (0-100)")
    @music_only()
    async def volume(interaction: discord.Interaction, valor: int):
        vc: discord.VoiceClient = interaction.guild.voice_client
        data = get_guild_data(interaction.guild.id)
        vol = max(0, min(valor, 100))
        data["volume"] = vol / 100.0
        if vc and vc.source and hasattr(vc.source, 'volume'):
            vc.source.volume = data["volume"]
        await interaction.response.send_message(f"🔊 Volume: **{vol}%**", ephemeral=True)

    # ── /shuffle ─────────────────────────────────────────────────────────────
    @tree.command(name="shuffle", description="🔀 Embaralha a fila de músicas")
    @music_only()
    async def shuffle(interaction: discord.Interaction):
        data = get_guild_data(interaction.guild.id)
        if data["queue"]:
            random.shuffle(data["queue"])
            await interaction.response.send_message(
                f"🔀 Fila embaralhada! ({len(data['queue'])} músicas)", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Fila vazia.", ephemeral=True)

    # ── /repeat ──────────────────────────────────────────────────────────────
    @tree.command(name="repeat", description="🔁 Ativa/desativa repetição da música atual")
    @music_only()
    async def repeat(interaction: discord.Interaction):
        data = get_guild_data(interaction.guild.id)
        data["repeat"] = not data["repeat"]
        status = "**ativada** 🔁" if data["repeat"] else "**desativada**"
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

            if not interaction.user.voice:
                await interaction.followup.send("❌ Entre em um canal de voz!", ephemeral=True)
                return

            vc: discord.VoiceClient = interaction.guild.voice_client
            if vc is None:
                vc = await interaction.user.voice.channel.connect(timeout=30.0, self_deaf=True)

            data = get_guild_data(interaction.guild.id)
            count = 0
            for q in playlists[uid][nome]:
                track = await search_track(q)
                if track:
                    data["queue"].append(track)
                    count += 1

            if not vc.is_playing() and data["queue"]:
                track = data["queue"].pop(0)
                data["current"] = track
                source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTS)
                source = discord.PCMVolumeTransformer(source, volume=data["volume"])

                def after_play(error):
                    if error:
                        print(f"[FILA] ❌ Erro: {error}", flush=True)
                    asyncio.run_coroutine_threadsafe(play_next(interaction.guild), bot.loop)

                vc.play(source, after=after_play)

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