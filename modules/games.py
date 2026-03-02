import discord
from discord import app_commands
import random
import asyncio
import aiohttp
from config import *

active_games = {}  # {channel_id: game_data}

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

WEBTOONS = [
    {"title": "Tower of God",       "hint": "Um garoto entra numa torre misteriosa para encontrar sua amiga"},
    {"title": "Solo Leveling",      "hint": "Um caçador fraco se torna o mais forte após um dungeon especial"},
    {"title": "The God of High School", "hint": "Um torneio de artes marciais com poderes divinos"},
    {"title": "Noblesse",           "hint": "Um nobre poderoso acorda após 820 anos de sono"},
    {"title": "Unordinary",         "hint": "Em um mundo com superpoderes, um garoto finge ser normal"},
    {"title": "Lore Olympus",       "hint": "Releitura moderna do mito de Perséfone e Hades"},
    {"title": "True Beauty",        "hint": "Uma garota usa maquiagem para esconder sua verdadeira aparência"},
    {"title": "SubZero",            "hint": "Princesa de dragão e príncipe de clã inimigo forçados a casar"},
]

QUIZ_FALLBACK = [
    {"q": "Qual é o nome do protagonista de Solo Leveling?",        "a": "sung jinwoo",      "opt": ["Sung Jinwoo","Cha Hae-In","Go Gunhee","Baek Yoonho"]},
    {"q": "De qual país são originários a maioria dos webtoons?",   "a": "coreia do sul",    "opt": ["Coreia do Sul","Japão","China","Brasil"]},
    {"q": "Qual plataforma é mais famosa por webtoons?",            "a": "webtoon",          "opt": ["Webtoon","Shonen Jump","Crunchyroll","Tapas"]},
    {"q": "Em Tower of God, o que Bam busca na torre?",             "a": "rachel",           "opt": ["Rachel","Khun","Rak","Endorsi"]},
    {"q": "Qual gênero de anime/manga é focado em herói jovem?",    "a": "shonen",           "opt": ["Shonen","Seinen","Josei","Shoujo"]},
]

FORCA_WORDS = [
    ("webtoon",    "Formato de quadrinho digital lido verticalmente"),
    ("mangá",      "Quadrinho japonês lido da direita para esquerda"),
    ("personagem", "Ser fictício de uma história"),
    ("episódio",   "Capítulo de uma série"),
    ("arco",       "Conjunto de capítulos com uma história"),
    ("vilão",      "Antagonista da história"),
    ("herói",      "Protagonista que luta pelo bem"),
    ("fantasia",   "Gênero com magia e mundos imaginários"),
    ("romance",    "Gênero focado em relacionamentos amorosos"),
    ("ação",       "Gênero com batalhas e aventuras"),
]

SLOT_SYMBOLS = ["🍒","🍋","🍊","⭐","💎","🎰","🐱"]


async def ai_generate_question() -> dict:
    """Gera pergunta de quiz via NVIDIA NIM."""
    if not NVIDIA_API_KEY:
        return random.choice(QUIZ_FALLBACK)
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "meta/llama-3.1-8b-instruct",
                "messages": [{
                    "role": "user",
                    "content": (
                        "Crie UMA pergunta de quiz sobre anime, manga, webtoon ou cultura pop japonesa/coreana em português brasileiro. "
                        "Responda APENAS em JSON sem markdown no formato: "
                        '{"q":"pergunta aqui","a":"resposta correta em minúsculas","opt":["Opção1","Opção2","Opção3","Opção4"]} '
                        "A resposta correta deve estar nas opções. Sem texto extra."
                    )
                }],
                "max_tokens": 200,
                "temperature": 0.9
            }
            async with session.post(
                NVIDIA_API_URL,
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data    = await resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    import json, re
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        return json.loads(match.group())
    except:
        pass
    return random.choice(QUIZ_FALLBACK)


async def ai_forca_hint(word: str, hint: str, wrong: list) -> str:
    """Gera dica inteligente para a forca via IA."""
    if not NVIDIA_API_KEY:
        return f"💡 Dica: {hint}"
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "meta/llama-3.1-8b-instruct",
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Crie UMA dica criativa em português para a palavra '{word}' no contexto de webtoons/anime. "
                        f"A dica original é: '{hint}'. Letras erradas: {wrong}. "
                        "Responda APENAS com a dica, sem introdução, sem aspas."
                    )
                }],
                "max_tokens": 80,
                "temperature": 0.7
            }
            async with session.post(
                NVIDIA_API_URL,
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return f"💡 {data['choices'][0]['message']['content'].strip()}"
    except:
        pass
    return f"💡 Dica: {hint}"


def setup_commands(tree: app_commands.CommandTree, bot):

    # ── QUIZ ──────────────────────────────────────────────────

    @tree.command(name="quiz", description="🧠 Responda uma pergunta de cultura pop")
    @channel_only(GAMES_CHANNEL)
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.channel.id)
    async def quiz(interaction: discord.Interaction):
        await interaction.response.defer()
        q_data = await ai_generate_question()
        opts   = q_data["opt"]
        random.shuffle(opts)
        labels = ["🅰️","🅱️","🅲️","🅳️"]
        desc   = "\n".join([f"{labels[i]} {o}" for i, o in enumerate(opts)])

        embed = discord.Embed(
            title="🧠 Quiz — Cultura Pop",
            description=f"**{q_data['q']}**\n\n{desc}\n\nVocê tem **20 segundos**!",
            color=0xFF6B9D
        )
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        for e in labels[:len(opts)]: await msg.add_reaction(e)

        react_map = {labels[i]: o for i, o in enumerate(opts)}
        correct_label = next((labels[i] for i, o in enumerate(opts) if o.lower() == q_data["a"].lower()), None)

        def check(reaction, user):
            return (not user.bot and reaction.message.id == msg.id and str(reaction.emoji) in labels)

        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=20.0, check=check)
            if str(reaction.emoji) == correct_label:
                bonus = 30
                data  = get_xp(interaction.guild.id, user.id)
                data["xp"] = data.get("xp",0) + bonus; data["total_xp"] = data.get("total_xp",0) + bonus
                set_xp(interaction.guild.id, user.id, data)
                await interaction.channel.send(f"✅ {user.mention} acertou! **+{bonus} XP**")
            else:
                await interaction.channel.send(f"❌ {user.mention} errou! A resposta era **{q_data['a'].title()}**")
        except asyncio.TimeoutError:
            await interaction.channel.send(f"⏰ Tempo esgotado! A resposta era **{q_data['a'].title()}**")


    # ── FORCA ─────────────────────────────────────────────────

    @tree.command(name="forca", description="🔤 Jogue forca com tema de webtoons")
    @channel_only(GAMES_CHANNEL)
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.channel.id)
    async def forca(interaction: discord.Interaction):
        if interaction.channel.id in active_games:
            await interaction.response.send_message("❌ Já há um jogo em andamento neste canal!", ephemeral=True)
            return

        word, hint = random.choice(FORCA_WORDS)
        game = {
            "word":    word.lower(),
            "hint":    hint,
            "guessed": [],
            "wrong":   [],
            "lives":   6,
            "channel": interaction.channel.id
        }
        active_games[interaction.channel.id] = game

        await interaction.response.send_message(embed=forca_embed(game))

        def check(m):
            return (m.channel.id == interaction.channel.id and
                    not m.author.bot and
                    len(m.content) == 1 and
                    m.content.isalpha())

        while game["lives"] > 0:
            display = " ".join([c if c in game["guessed"] else "\_" for c in game["word"]])
            if "_" not in display:
                winner_member = msg.author if "msg" in dir() else interaction.user
                data = get_xp(interaction.guild.id, winner_member.id)
                data["xp"] = data.get("xp",0)+50; data["total_xp"] = data.get("total_xp",0)+50
                set_xp(interaction.guild.id, winner_member.id, data)
                await interaction.channel.send(f"🎉 {winner_member.mention} adivinhou! A palavra era **{word}**! **+50 XP**")
                break

            try:
                msg = await bot.wait_for("message", timeout=30.0, check=check)
                letter = msg.content.lower()
                if letter in game["guessed"] or letter in game["wrong"]:
                    await msg.add_reaction("🔄"); continue
                if letter in game["word"]:
                    game["guessed"].append(letter)
                    await msg.add_reaction("✅")
                else:
                    game["wrong"].append(letter)
                    game["lives"] -= 1
                    await msg.add_reaction("❌")
                    if game["lives"] == 3:
                        ai_hint = await ai_forca_hint(word, hint, game["wrong"])
                        await interaction.channel.send(ai_hint)

                await interaction.channel.send(embed=forca_embed(game))

            except asyncio.TimeoutError:
                await interaction.channel.send(f"⏰ Tempo esgotado! A palavra era **{word}**")
                break
        else:
            await interaction.channel.send(f"💀 Você perdeu! A palavra era **{word}**")


        active_games.pop(interaction.channel.id, None)


    def forca_embed(game):
        display = " ".join([c if c in game["guessed"] else "\\_" for c in game["word"]])
        lives_bar = "❤️" * game["lives"] + "🖤" * (6 - game["lives"])
        return discord.Embed(
            title="🔤 Forca",
            description=(
                f"`{display}`\n\n"
                f"{lives_bar}\n"
                f"**Erradas:** {', '.join(game['wrong']) or 'Nenhuma'}\n"
                f"**Dica:** {game['hint']}\n\n"
                "Digite uma letra no chat!"
            ),
            color=0xFF6B9D
        )


    # ── ADIVINHE O WEBTOON ────────────────────────────────────

    @tree.command(name="adivinhe", description="🃏 Adivinhe o webtoon pela sinopse")
    @channel_only(GAMES_CHANNEL)
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.channel.id)
    async def adivinhe(interaction: discord.Interaction):
        w = random.choice(WEBTOONS)
        embed = discord.Embed(
            title="🃏 Adivinhe o Webtoon!",
            description=f"**Sinopse:** {w['hint']}\n\nDigite o nome no chat! Você tem **30 segundos**.",
            color=0xFF6B9D
        )
        await interaction.response.send_message(embed=embed)

        def check(m):
            return m.channel.id == interaction.channel.id and not m.author.bot

        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            if w["title"].lower() in msg.content.lower():
                data = get_xp(interaction.guild.id, msg.author.id)
                data["xp"] = data.get("xp",0)+40; data["total_xp"] = data.get("total_xp",0)+40
                set_xp(interaction.guild.id, msg.author.id, data)
                await interaction.channel.send(f"🎉 {msg.author.mention} acertou! **+40 XP**")
            else:
                await interaction.channel.send(f"❌ Errou! Era **{w['title']}**")
        except asyncio.TimeoutError:
            await interaction.channel.send(f"⏰ Tempo esgotado! Era **{w['title']}**")


    # ── SLOT MACHINE ──────────────────────────────────────────

    @tree.command(name="slot", description="🎰 Aposte XP na slot machine")
    @channel_only(GAMES_CHANNEL)
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def slot(interaction: discord.Interaction, aposta: int = 50):
        data = get_xp(interaction.guild.id, interaction.user.id)
        if data.get("total_xp", 0) < aposta:
            await interaction.response.send_message(f"❌ XP insuficiente! Você tem **{data.get('total_xp',0)} XP**.", ephemeral=True)
            return
        if aposta < 10 or aposta > 500:
            await interaction.response.send_message("❌ Aposta entre 10 e 500 XP.", ephemeral=True)
            return

        s = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        result = f"| {s[0]} | {s[1]} | {s[2]} |"

        if s[0] == s[1] == s[2] == "💎":
            ganho = aposta * 10; msg = f"💎 JACKPOT! **+{ganho} XP**!"
        elif s[0] == s[1] == s[2]:
            ganho = aposta * 3;  msg = f"🎉 Três iguais! **+{ganho} XP**!"
        elif s[0] == s[1] or s[1] == s[2]:
            ganho = aposta;      msg = f"✅ Dois iguais! Recuperou a aposta!"
        else:
            ganho = -aposta;     msg = f"❌ Perdeu **{aposta} XP**!"

        data["total_xp"] = max(0, data.get("total_xp",0) + ganho)
        if ganho > 0:
            data["xp"] = data.get("xp",0) + ganho
        set_xp(interaction.guild.id, interaction.user.id, data)

        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"```\n{result}\n```\n{msg}\n**XP Total:** {data['total_xp']}",
            color=0xFF6B9D if ganho > 0 else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)


    # ── DUELO DE XP ───────────────────────────────────────────

    @tree.command(name="duelo", description="⚔️ Desafia outro membro para um duelo de XP")
    @channel_only(GAMES_CHANNEL)
    async def duelo(interaction: discord.Interaction, oponente: discord.Member, aposta: int = 100):
        if oponente.bot or oponente.id == interaction.user.id:
            await interaction.response.send_message("❌ Oponente inválido.", ephemeral=True)
            return

        data1 = get_xp(interaction.guild.id, interaction.user.id)
        data2 = get_xp(interaction.guild.id, oponente.id)
        if data1.get("total_xp",0) < aposta or data2.get("total_xp",0) < aposta:
            await interaction.response.send_message("❌ Um dos jogadores não tem XP suficiente.", ephemeral=True)
            return

        view = DuelView(interaction.user, oponente, aposta, interaction.guild.id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⚔️ Desafio de Duelo!",
                description=f"{oponente.mention}, {interaction.user.mention} te desafiou para um duelo de **{aposta} XP**!\nClique em Aceitar ou Recusar.",
                color=0xFF6B9D
            ),
            view=view
        )


    class DuelView(discord.ui.View):
        def __init__(self, challenger, opponent, bet, guild_id):
            super().__init__(timeout=30)
            self.challenger = challenger
            self.opponent   = opponent
            self.bet        = bet
            self.guild_id   = guild_id

        @discord.ui.button(label="✅ Aceitar", style=discord.ButtonStyle.success)
        async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.opponent.id:
                await interaction.response.send_message("❌ Só o desafiado pode aceitar!", ephemeral=True); return
            import random as r
            winner  = r.choice([self.challenger, self.opponent])
            loser   = self.opponent if winner == self.challenger else self.challenger
            d_win   = get_xp(self.guild_id, winner.id)
            d_lose  = get_xp(self.guild_id, loser.id)
            d_win["total_xp"]  = d_win.get("total_xp",0)  + self.bet
            d_win["xp"]        = d_win.get("xp",0)        + self.bet
            d_lose["total_xp"] = max(0, d_lose.get("total_xp",0) - self.bet)
            set_xp(self.guild_id, winner.id, d_win)
            set_xp(self.guild_id, loser.id,  d_lose)
            self.stop()
            await interaction.response.edit_message(embed=discord.Embed(
                title="⚔️ Resultado do Duelo!",
                description=f"🏆 {winner.mention} venceu e ganhou **{self.bet} XP**!\n💸 {loser.mention} perdeu **{self.bet} XP**.",
                color=discord.Color.gold()
            ), view=None)

        @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.danger)
        async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.opponent.id:
                await interaction.response.send_message("❌ Só o desafiado pode recusar!", ephemeral=True); return
            self.stop()
            await interaction.response.edit_message(embed=discord.Embed(
                description=f"❌ {self.opponent.mention} recusou o duelo.",
                color=discord.Color.red()
            ), view=None)


    # ── COMPLETE A HISTÓRIA ───────────────────────────────────

    stories = {}  # {channel_id: [frases]}

    @tree.command(name="historia", description="📝 Adicione uma frase à história coletiva")
    @channel_only(GAMES_CHANNEL)
    async def historia(interaction: discord.Interaction, frase: str):
        cid = interaction.channel.id
        if cid not in stories: stories[cid] = []
        if len(frase) > 150:
            await interaction.response.send_message("❌ Máximo 150 caracteres por frase.", ephemeral=True); return
        stories[cid].append(f"**{interaction.user.display_name}:** {frase}")
        texto = "\n".join(stories[cid][-10:])
        embed = discord.Embed(
            title="📝 História Coletiva",
            description=texto + "\n\n*Use `/historia [frase]` para continuar!*",
            color=0xFF6B9D
        )
        embed.set_footer(text=f"Total de frases: {len(stories[cid])}")
        await interaction.response.send_message(embed=embed)
        if len(stories[cid]) % 20 == 0:
            data = get_xp(interaction.guild.id, interaction.user.id)
            data["xp"] = data.get("xp",0)+20; data["total_xp"] = data.get("total_xp",0)+20
            set_xp(interaction.guild.id, interaction.user.id, data)
            await interaction.channel.send(f"🎉 Marco de **{len(stories[cid])} frases**! +20 XP para {interaction.user.mention}")


    # ── VOTAÇÃO DE ARTE ───────────────────────────────────────

    art_votes = {}  # {message_id: {user_id: artista_id}}

    @tree.command(name="votararte", description="🎨 Submeta sua arte para votação")
    @channel_only(GAMES_CHANNEL)
    async def votararte(interaction: discord.Interaction, descricao: str, imagem_url: str):
        embed = discord.Embed(
            title="🎨 Votação de Arte",
            description=f"**Artista:** {interaction.user.mention}\n**Descrição:** {descricao}\n\nReaja com ❤️ para votar!",
            color=0xFF6B9D
        )
        embed.set_image(url=imagem_url)
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("❤️")
        art_votes[msg.id] = {"artist": interaction.user.id, "votes": 0}