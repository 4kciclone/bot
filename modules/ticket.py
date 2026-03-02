import discord
from discord import app_commands
import datetime
import asyncio
from config import *

async def send_ticket_panel(channel: discord.TextChannel):
    embed = discord.Embed(
        title="🎫 Central de Suporte — Gato Comics",
        description="Selecione a categoria do seu problema abaixo.\nUm canal privado será aberto só para você e nossa equipe. 🐱",
        color=0xFF6B9D
    )
    embed.set_footer(text="Apenas você e a equipe verão seu ticket.")
    await channel.send(embed=embed, view=TicketCategoryView())


class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o tipo de suporte...",
            custom_id="ticket_category",
            options=[
                discord.SelectOption(label="Problema de Leitura", emoji="📖", value="leitura",   description="Erro ao ler um webtoon"),
                discord.SelectOption(label="Dúvida sobre Obra",   emoji="📚", value="obra",      description="Perguntas sobre algum título"),
                discord.SelectOption(label="Pagamento",           emoji="💳", value="pagamento", description="Problema com assinatura ou compra"),
                discord.SelectOption(label="Bug Técnico",         emoji="🐛", value="bug",       description="Erro técnico na plataforma"),
                discord.SelectOption(label="Quero ser Parceiro",  emoji="🤝", value="parceria",  description="Interesse em publicar na Gato Comics"),
                discord.SelectOption(label="Outros",              emoji="❓", value="outros",    description="Qualquer outro assunto"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        cat_map = {
            "leitura":   ("📖 Leitura",   "Descreva qual webtoon e qual o problema ao ler."),
            "obra":      ("📚 Obra",      "Qual o título da obra e sua dúvida?"),
            "pagamento": ("💳 Pagamento", "Descreva o problema com pagamento ou assinatura."),
            "bug":       ("🐛 Bug",       "Descreva o erro (dispositivo, versão, etc)."),
            "parceria":  ("🤝 Parceria",  "Conte sobre você e seu projeto!"),
            "outros":    ("❓ Outros",    "Descreva sua dúvida ou solicitação."),
        }
        cat_name, first_msg = cat_map[self.values[0]]
        guild = interaction.guild
        user  = interaction.user
        slug  = user.name.lower().replace(' ', '-')[:20]
        ticket_name = f"ticket-{slug}"

        existing = discord.utils.get(guild.channels, name=ticket_name)
        if existing:
            await interaction.response.send_message(f"❌ Você já tem um ticket: {existing.mention}", ephemeral=True)
            return

        cat = discord.utils.get(guild.categories, name=TICKET_CATEGORY) or await guild.create_category(TICKET_CATEGORY)
        support = [r for r in guild.roles if r.name in SUPPORT_ROLE_NAMES]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        }
        for r in support:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

        ch = await guild.create_text_channel(
            ticket_name, category=cat, overwrites=overwrites,
            topic=f"{cat_name} | {user.name} | {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

        embed = discord.Embed(
            title=f"🎫 Ticket — {cat_name}",
            description=f"Olá {user.mention}! 👋\n\n**{first_msg}**\n\nNossa equipe responderá em breve.\nQuando resolvido, clique em **🔒 Fechar Ticket**.",
            color=0xFF6B9D, timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Gato Comics Support 🐱")
        mentions = " ".join(r.mention for r in support)
        await ch.send(content=f"{user.mention} {mentions}", embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"✅ Ticket aberto: {ch.mention}", ephemeral=True)

        # Atualizar stats
        await update_ticket_stats(guild, 1)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch    = interaction.channel
        guild = interaction.guild
        support  = [r for r in interaction.user.roles if r.name in SUPPORT_ROLE_NAMES]
        is_owner = ch.name.endswith(interaction.user.name.lower().replace(' ', '-')[:20])
        if not support and not is_owner:
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Fechando em 5 segundos...")
        log_ch = discord.utils.get(guild.channels, name=LOG_CHANNEL)
        if log_ch:
            msgs = [
                f"[{m.created_at.strftime('%d/%m %H:%M')}] {m.author.display_name}: {m.content}"
                async for m in ch.history(limit=200, oldest_first=True) if not m.author.bot
            ]
            embed = discord.Embed(
                title=f"📋 Ticket Fechado — #{ch.name}",
                description=f"Fechado por: {interaction.user.mention}\n\n**Log:**\n```\n" + "\n".join(msgs[-30:]) + "\n```",
                color=discord.Color.red(), timestamp=datetime.datetime.utcnow()
            )
            await log_ch.send(embed=embed)

        await asyncio.sleep(5)
        await ch.delete()
        await update_ticket_stats(guild, -1)


async def update_ticket_stats(guild: discord.Guild, delta: int):
    """Atualiza o canal de estatísticas de tickets."""
    for ch in guild.voice_channels:
        if ch.name.startswith("🎫 Tickets:"):
            try:
                current = int(ch.name.split(": ")[1])
                await ch.edit(name=f"🎫 Tickets: {max(0, current + delta)}")
            except:
                pass
            break


def setup_commands(tree: app_commands.CommandTree, bot):

    @tree.command(name="ticketpainel", description="📩 Reenvia o painel de tickets")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticket_panel_cmd(interaction: discord.Interaction):
        await send_ticket_panel(interaction.channel)
        await interaction.response.send_message("✅ Painel enviado!", ephemeral=True)