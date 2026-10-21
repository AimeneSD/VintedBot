import discord
from discord.ext import commands
from aiohttp_socks import ProxyConnector
import os
from dotenv import load_dotenv
import utils.database as db
import utils.keep_alive as keep_alive

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

class VintedBot(commands.Bot):
    def __init__(self):
        connector = ProxyConnector.from_url("socks5://127.0.0.1:1080")
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.default(),
            connector=connector,
        )

    async def setup_hook(self):
        # Charger les extensions (Cogs)
        await self.load_extension("cogs.sniper")
        await self.load_extension("cogs.commands")
        
        await self.tree.sync()
        print("Commandes Slash synchronisées globalement")
        
        # Initialisation asynchrone MySQL
        await db.init_db()
        await db.clean_old_vinted_items()
        
        # Lancement du serveur web pour Render
        self.loop.create_task(keep_alive.start_server())

    async def on_ready(self):
        print(f"Bot connecté en tant que {self.user}")

if __name__ == "__main__":
    if not TOKEN:
        print("Erreur: DISCORD_BOT_TOKEN manquant dans le fichier .env")
    else:
        bot = VintedBot()
        bot.run(TOKEN)
