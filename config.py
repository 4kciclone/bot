import os
from dotenv import load_dotenv

load_dotenv()

TOKEN            = os.getenv("TOKEN")
GUILD_ID         = int(os.getenv("GUILD_ID", 0))
NVIDIA_API_KEY   = os.getenv("NVIDIA_API_KEY")

# Canais
TICKET_CHANNEL   = os.getenv("TICKET_CHANNEL",   "🎫・abrir-ticket")
ANNOUNCE_CHANNEL = os.getenv("ANNOUNCE_CHANNEL", "📣・anúncios")
LAUNCH_CHANNEL   = os.getenv("LAUNCH_CHANNEL",   "🚀・lançamentos")
RANKING_CHANNEL  = os.getenv("RANKING_CHANNEL",  "🏆・ranking")
CONQUEST_CHANNEL = os.getenv("CONQUEST_CHANNEL", "⭐・conquistas")
WELCOME_CHANNEL  = os.getenv("WELCOME_CHANNEL",  "🎉・boas-vindas")
COMMANDS_CHANNEL = os.getenv("COMMANDS_CHANNEL", "🤖・comandos-bot")
RULES_CHANNEL    = os.getenv("RULES_CHANNEL",    "📋・regras")
UPDATES_CHANNEL  = os.getenv("UPDATES_CHANNEL",  "📣・anúncios")
LOG_CHANNEL      = os.getenv("LOG_CHANNEL",      "📋・log-tickets")
LOG_MOD_CHANNEL  = os.getenv("LOG_MOD_CHANNEL",  "🔨・log-moderação")
POLL_CHANNEL     = os.getenv("POLL_CHANNEL",     "📊・enquetes")
GIVEAWAY_CHANNEL = os.getenv("GIVEAWAY_CHANNEL", "🎁・sorteios")
STATS_CATEGORY   = os.getenv("STATS_CATEGORY",   "📊 ESTATÍSTICAS")

WARNS_MUTE       = int(os.getenv("WARNS_MUTE", 3))
WARNS_BAN        = int(os.getenv("WARNS_BAN",  5))
XP_PER_MESSAGE   = int(os.getenv("XP_PER_MESSAGE", 15))
SPAM_LIMIT       = int(os.getenv("SPAM_LIMIT", 5))
SPAM_SECONDS     = int(os.getenv("SPAM_SECONDS", 3))

SUPPORT_ROLE_NAMES = ["👑 Owner", "⚙️ Admin", "🛡️ Moderador"]
TICKET_CATEGORY    = "🎫 TICKETS"
LEVEL_ROLES        = {5: "📖 Leitor", 15: "💎 Leitor VIP", 30: "⭐ Veterano"}

# Dados em memória compartilhados entre módulos
xp_data       = {}
warns_data    = {}
giveaways     = {}
streaks       = {}
missions_done = {}
shop_items    = {
    "🌟 Destaque":        {"price": 500,  "role": "🌟 Destaque"},
    "💜 Apoiador":        {"price": 1000, "role": "💜 Apoiador"},
    "🔥 Lenda":           {"price": 3000, "role": "🔥 Lenda"},
    "🎭 Contador de Histórias": {"price": 800, "role": "🎭 Contador de Histórias"},
}

def get_xp(gid, uid):
    return xp_data.get(str(gid), {}).get(str(uid), {"xp": 0, "level": 1, "messages": 0, "total_xp": 0})

def set_xp(gid, uid, data):
    g, u = str(gid), str(uid)
    if g not in xp_data: xp_data[g] = {}
    xp_data[g][u] = data

def xp_needed(level):
    return 100 * (level ** 2)

def get_warns(gid, uid):
    return warns_data.get(str(gid), {}).get(str(uid), [])

def add_warn(gid, uid, reason, by):
    g, u = str(gid), str(uid)
    if g not in warns_data: warns_data[g] = {}
    if u not in warns_data[g]: warns_data[g][u] = []
    import datetime
    warns_data[g][u].append({"reason": reason, "by": str(by), "at": datetime.datetime.utcnow().isoformat()})
    return len(warns_data[g][u])

def channel_only(channel_names: list):
    from discord import app_commands
    async def predicate(interaction):
        import discord
        # Se for uma string única, transforma em lista para compatibilidade
        targets = [channel_names] if isinstance(channel_names, str) else channel_names
        
        current_ch = interaction.channel.name
        if not any(name == current_ch for name in targets):
            mentions = ", ".join([f"#{n}" for n in targets])
            await interaction.response.send_message(f"❌ Use este comando em: {mentions}!", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

def staff_only():
    from discord import app_commands
    async def predicate(interaction):
        roles = [r.name for r in interaction.user.roles]
        if not any(r in SUPPORT_ROLE_NAMES for r in roles):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)