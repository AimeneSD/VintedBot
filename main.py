import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialisation du bot
class VintedBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Commandes Slash synchronisées globalement")

bot = VintedBot()

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

@bot.tree.command(name="ping", description="Vérifie si le bot VintedBot est en ligne")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! Le sniper Vinted est prêt à tirer.", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("Erreur: DISCORD_BOT_TOKEN manquant dans le fichier .env")
    else:
        bot.run(TOKEN)
