import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CONFIG_FILE = "data/config_vinted.json"

# --- Gestion de la Configuration ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception as e:
                print(f"Erreur lecture config: {e}")
    return {}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

config_surveillances = load_config()
# -----------------------------------

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

@bot.tree.command(name="vinted_add", description="Ajoute une recherche Vinted à surveiller via son URL")
@app_commands.describe(url="L'URL de ta recherche (ex: https://www.vinted.fr/catalog?...)")
async def vinted_add(interaction: discord.Interaction, url: str):
    user_id = str(interaction.user.id)
    
    if "vinted." not in url:
        await interaction.response.send_message("❌ L'URL ne semble pas être une URL Vinted valide.", ephemeral=True)
        return
        
    if user_id not in config_surveillances:
        config_surveillances[user_id] = []
        
    if url in config_surveillances[user_id]:
        await interaction.response.send_message("❌ Tu surveilles déjà cette recherche !", ephemeral=True)
        return
        
    config_surveillances[user_id].append(url)
    save_config(config_surveillances)
    
    await interaction.response.send_message(
        f"✅ **Surveillance Vinted ajoutée avec succès !**\n"
        f"Je te préviendrai en MP dès qu'une nouvelle annonce correspondant à ces critères sera publiée.\n\n"
        f"🔗 *URL surveillée : <{url}>*", 
        ephemeral=True
    )

@bot.tree.command(name="vinted_list", description="Affiche la liste de tes surveillances Vinted actives")
async def vinted_list(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    urls = config_surveillances.get(user_id, [])
    
    if not urls:
        await interaction.response.send_message("Tu n'as aucune surveillance Vinted active pour le moment. Utilise `/vinted_add`.", ephemeral=True)
        return
        
    msg = "**🎯 Tes surveillances Vinted actives :**\n\n"
    for i, url in enumerate(urls, 1):
        msg += f"**{i}.** <{url}>\n"
        
    await interaction.response.send_message(msg, ephemeral=True)

async def autocomplete_vinted_urls(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    user_id = str(interaction.user.id)
    urls = config_surveillances.get(user_id, [])
    # L'autocomplétion filtre les URL en fonction de ce qui est tapé
    matches = [u for u in urls if current.lower() in u.lower()]
    # Discord limite la longueur du nom des choix à 100 caractères
    return [app_commands.Choice(name=u[:100] + ("..." if len(u) > 100 else ""), value=u) for u in matches][:25]

@bot.tree.command(name="vinted_remove", description="Supprime une de tes surveillances Vinted")
@app_commands.describe(url="Choisis l'URL de la surveillance à supprimer")
@app_commands.autocomplete(url=autocomplete_vinted_urls)
async def vinted_remove(interaction: discord.Interaction, url: str):
    user_id = str(interaction.user.id)
    urls = config_surveillances.get(user_id, [])
    
    if url in urls:
        urls.remove(url)
        save_config(config_surveillances)
        await interaction.response.send_message("🗑️ **Surveillance supprimée avec succès.** Je ne chercherai plus cette URL.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Cette URL n'est pas dans ta liste de surveillances.", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("Erreur: DISCORD_BOT_TOKEN manquant dans le fichier .env")
    else:
        bot.run(TOKEN)
