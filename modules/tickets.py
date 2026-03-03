import discord
from discord.ext import commands

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Problema de Leitura', description='Páginas não carregam ou erro no app', emoji='📖'),
            discord.SelectOption(label='Problema no Pagamento', description='Moedas não caíram ou erro no cartão', emoji='💳'),
            discord.SelectOption(label='Bug no Site', description='Encontrei um erro visual ou de sistema', emoji='🐛'),
            discord.SelectOption(label='Dúvidas Gerais', description='Quero falar com um membro da equipe', emoji='❓')
        ]
        # Custom_id garante que o bot lembre do dropdown se reiniciar
        super().__init__(placeholder='Escolha o departamento adequado...', min_values=1, max_values=1, options=options, custom_id='ticket_dropdown')

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        category = discord.utils.get(guild.categories, name="🎟️ TICKETS")
        
        if not category:
            # Tenta criar a categoria se alguém apagou
            try:
                category = await guild.create_category("🎟️ TICKETS")
            except:
                return await interaction.response.send_message("❌ Erro: Não encontrei a categoria de Tickets. Avise a Staff.", ephemeral=True)

        # Verifica se o usuário já tem um ticket aberto
        for channel in category.channels:
            if f"ticket-{member.name}".lower() in channel.name.lower():
                return await interaction.response.send_message("⚠️ Você já tem um ticket aberto nesta categoria.", ephemeral=True)

        # Configura as permissões do novo canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        }
        
        # Admin e Fundador
        admin_roles = ["👑 Fundador / Sócio", "👑 Administrador", "🎧 Equipe de Suporte"]
        for role_name in admin_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                 overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Cria o canal
        try:
            ticket_channel = await guild.create_text_channel(
                f"ticket-{member.name}",
                category=category,
                overwrites=overwrites
            )
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erro ao criar o canal: {e}", ephemeral=True)

        # Responder ao usuário (ephemeral = só ele vê)
        await interaction.response.send_message(f"✅ Ticket criado em {ticket_channel.mention}!", ephemeral=True)

        # Enviar mensagem dentro do novo canal
        embed = discord.Embed(
            title=f"Ticket: {self.values[0]}",
            description=(
                f"Olá {member.mention}! Nossa equipe já foi notificada e em breve fará o atendimento.\n\n"
                "Descreva seu problema com o máximo de detalhes possível, anexe prints se puder.\n\n"
                "Para encerrar o atendimento, clique no botão abaixo."
            ),
            color=discord.Color.gold()
        )
        
        view = CloseTicketView()
        await ticket_channel.send(embed=embed, view=view)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("O ticket será fechado e deletado em 5 segundos...")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))
        try:
            await interaction.channel.delete()
        except:
            pass


class TicketSystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='setup_tickets', help='[Admin] Instancia o painel de tickets de suporte dinâmico no canal atual.')
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        # Limpa o chat para deixar o painel limpo
        try:
           await ctx.channel.purge(limit=2) 
        except:
            pass

        embed = discord.Embed(
            title="📞 Central de Atendimento - Gato Comics",
            description=(
                "Precisa de ajuda com o aplicativo, pagamento de moedas ou quer reportar um bug?\n\n"
                "Selecione o departamento adequado no menu abaixo e **um canal privado** "
                "será aberto imediatamente para conversarmos com você."
            ),
            color=discord.Color.blue()
        )
        # Tenta pegar a logo do bot pro embed ficar mais rico
        if self.bot.user.display_avatar:
             embed.set_thumbnail(url=self.bot.user.display_avatar.url)
             
        # Envia o Embed + View com Dropdown
        await ctx.send(embed=embed, view=TicketSystemView())


async def setup(bot):
    await bot.add_cog(Tickets(bot))
