import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Carrega as variáveis de ambiente baseadas no .env
load_dotenv()

# Configura as intenções do bot (necessário para gerenciar cargos/membros, etc)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Necessário para interagir com os membros do servidor
intents.guilds = True  # Necessário para gerenciar canais e cargos

from modules.tickets import TicketSystemView, CloseTicketView

class GatoComicsBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )

    async def setup_hook(self):
        # Registra as Views persistentes (Tickets) para que os botões funcionem após reiniciar
        self.add_view(TicketSystemView())
        self.add_view(CloseTicketView())
        # Carrega todas as extensões (módulos / cogs) na pasta modules/
        for filename in os.listdir('./modules'):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await self.load_extension(f'modules.{filename[:-3]}')
                    print(f'Módulo carregado: {filename}')
                except Exception as e:
                    print(f'Erro ao carregar o módulo {filename}: {e}')

    async def on_ready(self):
        print(f'Bot conectado com sucesso como {self.user} (ID: {self.user.id})')
        print('Pronto para gerenciar a Gato Comics!')
        await self.change_presence(activity=discord.Game(name="Lendo Webtoons na Gato Comics"))

bot = GatoComicsBot()

if __name__ == '__main__':
    # Obtém o token do .env
    token = os.getenv('DISCORD_TOKEN')
    
    if token is None or token == 'seu_token_aqui':
        print("AVISO: Token do Discord não configurado. Por favor, adicione seu token no arquivo .env")
    else:
        bot.run(token)
