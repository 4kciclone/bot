import discord
from discord.ext import commands
import aiosqlite
import random
import time
import datetime

# Base de XP para subir de nível: Nível * 100
# Ex: Nível 1 -> 2 = 100 XP / Nível 2 -> 3 = 200 XP
def next_level_xp(level):
    return level * 100

class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "gato_comics.db"
        
    async def cog_load(self):
        # Cria a tabela de XP se não existir
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    last_message_time REAL DEFAULT 0,
                    last_daily_date TEXT DEFAULT ''
                )
            ''')
            await db.commit()

    async def get_user(self, user_id):
        # Retorna os dados do usuário ou cria um novo na tabela
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT xp, level, last_message_time, last_daily_date FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if not result:
                    await db.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
                    await db.commit()
                    return 0, 1, 0.0, ""
                return result

    async def update_user(self, user_id, xp, level, last_message_time, last_daily_date):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users 
                SET xp = ?, level = ?, last_message_time = ?, last_daily_date = ?
                WHERE user_id = ?
            ''', (xp, level, last_message_time, last_daily_date, user_id))
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        xp, level, last_msg_time, last_daily = await self.get_user(user_id)

        now = time.time()
        # Cooldown de 60 segundos por mensagem para ganhar XP
        if now - last_msg_time > 60:
            xp_ganho = random.randint(15, 25)
            novo_xp = xp + xp_ganho
            novo_lvl = level

            xp_necessario = next_level_xp(level)

            if novo_xp >= xp_necessario:
                novo_xp -= xp_necessario
                novo_lvl += 1
                
                # Envia mensagem de Level Up
                channel = message.channel
                await channel.send(f"🎉 Parabéns {message.author.mention}! Você subiu para o **Nível {novo_lvl}**! 🚀")

                # RECOMPENSAS DE CARGOS VIP
                # Verifica se o membro atingiu os níveis de premiação e dá o cargo, se existir.
                rewards = {
                    5: "🌟 Super Fã (VIP)",
                    10: "🎨 Artista Parceiro" 
                }
                if novo_lvl in rewards:
                    role_name = rewards[novo_lvl]
                    role = discord.utils.get(message.guild.roles, name=role_name)
                    if role:
                        try:
                            await message.author.add_roles(role, reason="Recompensa de Nível")
                            await channel.send(f"🎁 Incrível! Por atingir o Nível {novo_lvl}, você desbloqueou o cargo **{role_name}**!")
                        except:
                            pass # Bot sem permissão ou cargo acima dele na hierarquia

            await self.update_user(user_id, novo_xp, novo_lvl, now, last_daily)

    @commands.command(name='rank', aliases=['nivel', 'level'], help='Mostra o seu Nível e XP atual.')
    async def rank(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        if member.bot:
            return await ctx.send("🤖 Bots não possuem XP, eles já sabem tudo!")

        xp, level, _, _ = await self.get_user(member.id)
        xp_necessario = next_level_xp(level)

        embed = discord.Embed(title=f"💳 Perfil de Gato Comics", color=member.color or discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
        embed.add_field(name="Usuário", value=member.mention, inline=False)
        embed.add_field(name="🏆 Nível", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ XP Atual", value=f"{xp} / {xp_necessario}", inline=True)

        # Calculo rudimentar da barra de progresso
        progress = int((xp / xp_necessario) * 10)
        barra = ("🟩" * progress) + ("🔲" * (10 - progress))
        embed.add_field(name="Progresso", value=barra, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name='daily', help='Ganha uma recompensa de XP diária.')
    async def daily(self, ctx):
        user_id = ctx.author.id
        xp, level, last_msg_time, last_daily = await self.get_user(user_id)

        # Usar data UTC para padronizar (YYYY-MM-DD)
        hoje = datetime.datetime.utcnow().strftime('%Y-%m-%d')

        if last_daily == hoje:
            return await ctx.send(f"⏳ Calma lá, {ctx.author.mention}! Você já pegou sua recompensa de Missão Diária hoje. Volte amanhã!")

        # Ganha um bonus parrudo de XP
        xp_bonus = random.randint(100, 200)
        novo_xp = xp + xp_bonus
        novo_lvl = level
        xp_necessario = next_level_xp(level)

        msg_extra = ""
        # Verifica level up por daily
        if novo_xp >= xp_necessario:
            novo_xp -= xp_necessario
            novo_lvl += 1
            msg_extra = f"\n🎉 Uau! Esse bônus fez você subir para o **Nível {novo_lvl}**!"

        await self.update_user(user_id, novo_xp, novo_lvl, last_msg_time, hoje)

        embed = discord.Embed(
            title="🎯 Missão Diária Concluída!", 
            description=f"Você acessou a comunidade hoje e encontrou **{xp_bonus} XP**! 🌟{msg_extra}", 
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name='top', aliases=['leaderboard'], help='Mostra os 10 membros com mais level no servidor.')
    async def top(self, ctx):
        async with aiosqlite.connect(self.db_path) as db:
            # Pega os Top 10 baseados no nível e depois pelo XP
            async with db.execute('SELECT user_id, xp, level FROM users ORDER BY level DESC, xp DESC LIMIT 10') as cursor:
                top_users = await cursor.fetchall()

        if not top_users:
            return await ctx.send("Ninguém ganhou XP ainda no servidor!")

        embed = discord.Embed(title="🏆 Rank de Leitores - Gato Comics", color=discord.Color.gold())
        
        desc = ""
        for i, (uid, xp, level) in enumerate(top_users, start=1):
            member = ctx.guild.get_member(uid)
            nome = member.display_name if member else f"Usuário Desconhecido"
            
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            prefix = medals.get(i, f"**{i}º**")
            
            desc += f"{prefix} **{nome}** — Nível `{level}` *(XP: {xp})*\n"

        embed.description = desc
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(XP(bot))
