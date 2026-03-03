import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, guild: discord.Guild, embed: discord.Embed):
        log_channel = discord.utils.get(guild.text_channels, name="log-moderação")
        if log_channel:
            await log_channel.send(embed=embed)

    @commands.command(name='limpar', help='[Admin/Mod] Limpa uma quantidade específica de mensagens do canal.')
    @commands.has_permissions(manage_messages=True)
    async def limpar(self, ctx, amount: int = 5):
        try:
            # Limita a deleção a 100 mensagens por vez por segurança
            amount = min(amount, 100)
            deleted = await ctx.channel.purge(limit=amount + 1) # +1 para apagar o próprio comando
            msg = await ctx.send(f"🧹 **{len(deleted)-1}** mensagens foram limpas por {ctx.author.mention}.")
            await msg.delete(delay=5)
            
            # Log
            embed = discord.Embed(title="🧹 Limpeza de Chat", color=discord.Color.light_grey())
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
            embed.add_field(name="Canal", value=ctx.channel.mention, inline=True)
            embed.add_field(name="Quantidade", value=str(len(deleted)-1), inline=True)
            await self.send_log(ctx.guild, embed)
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao limpar mensagens: {e}")

    @commands.command(name='kick', help='[Admin/Mod] Expulsa um membro do servidor. Exige motivo.')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str):
        if member == ctx.author:
            return await ctx.send("❌ Você não pode se expulsar!")
        
        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 **{member.display_name}** foi expulso do servidor. Motivo: {reason}")
            
            # Log
            embed = discord.Embed(title="👢 Membro Expulso (Kick)", color=discord.Color.orange())
            embed.add_field(name="Membro", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=False)
            embed.add_field(name="Motivo", value=reason, inline=False)
            await self.send_log(ctx.guild, embed)
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao expulsar membro: {e}")

    @commands.command(name='ban', help='[Admin/Mod] Bane um membro do servidor. Exige motivo.')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str):
        if member == ctx.author:
            return await ctx.send("❌ Você não pode se banir!")
            
        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 **{member.display_name}** foi banido do servidor. Motivo: {reason}")
            
            # Log
            embed = discord.Embed(title="🔨 Membro Banido", color=discord.Color.red())
            embed.add_field(name="Membro", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=False)
            embed.add_field(name="Motivo", value=reason, inline=False)
            await self.send_log(ctx.guild, embed)
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao banir membro: {e}")

    @commands.command(name='mute', help='[Admin/Mod] Muta temporariamente um membro (Timeout). Ex: !mute @user 10m flood')
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duracao: str, *, reason: str):
        if member == ctx.author:
            return await ctx.send("❌ Você não pode se mutar!")
            
        # Converter string '10m', '1h' etc em datetime.timedelta
        import datetime
        import re
        
        time_dict = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        match = re.match(r"(\d+)([smhd])", duracao.lower())
        if not match:
             return await ctx.send("❌ Formato de duração inválido. Use 's', 'm', 'h' ou 'd' (ex: 10m).")
             
        amount, unit = int(match.group(1)), match.group(2)
        seconds = amount * time_dict[unit]
        
        # Max timeout no Discord é 28 dias
        if seconds > 28 * 86400:
             return await ctx.send("❌ O timeout máximo permitido pelo Discord é de 28 dias.")
             
        duration_td = datetime.timedelta(seconds=seconds)
        
        try:
            await member.timeout(duration_td, reason=reason)
            await ctx.send(f"🔇 **{member.display_name}** foi mutado por {duracao}. Motivo: {reason}")
            
            # Log
            embed = discord.Embed(title="🔇 Membro Mutado (Timeout)", color=discord.Color.yellow())
            embed.add_field(name="Membro", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=False)
            embed.add_field(name="Duração", value=duracao, inline=False)
            embed.add_field(name="Motivo", value=reason, inline=False)
            await self.send_log(ctx.guild, embed)
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao mutar membro: {e}")

    @commands.command(name='unmute', help='[Admin/Mod] Remove o mute temporário de um membro.')
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = "Nenhum motivo especificado."):
        if member == ctx.author:
             return await ctx.send("❌ Hã???")
             
        try:
            await member.timeout(None, reason=reason)
            await ctx.send(f"🔊 O mute de **{member.display_name}** foi removido.")
            
            # Log
            embed = discord.Embed(title="🔊 Mute Removido", color=discord.Color.green())
            embed.add_field(name="Membro", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="Moderador", value=ctx.author.mention, inline=False)
            embed.add_field(name="Motivo", value=reason, inline=False)
            await self.send_log(ctx.guild, embed)
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao remover mute do membro: {e}")

    # Tratamento de erros das permissões
    @limpar.error
    @kick.error
    @ban.error
    @mute.error
    @unmute.error
    async def mod_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Você não tem permissão para usar este comando de moderação.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Faltam argumentos. Especifique quem e o motivo obrigatório. Use `!help {ctx.command}`.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
