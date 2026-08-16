import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
import random
from dotenv import load_dotenv
from utils.vinted import vinted_client

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CONFIG_FILE = "data/config_vinted.json"
CACHE_FILE = "data/offres_connues.json"

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

# --- Gestion du Cache des Annonces ---
def load_known_items():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception as e:
                print(f"Erreur lecture cache: {e}")
    return {}

def save_known_items(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)

known_items = load_known_items()

# -----------------------------------

class VintedBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.tree.sync()
        print("Commandes Slash synchronisees globalement")
        # Lancer la boucle de surveillance en arriere-plan
        self.loop.create_task(self.vinted_sniper_loop())

    async def vinted_sniper_loop(self):
        await self.wait_until_ready()
        print("Demarrage de la boucle de surveillance Vinted...")
        while not self.is_closed():
            # Delai aleatoire entre 23 et 27 secondes pour imiter un comportement humain
            delay = random.uniform(23, 27)
            await asyncio.sleep(delay)
            
            # Recuperer toutes les URLs uniques a verifier
            all_urls = set()
            for urls in config_surveillances.values():
                for u in urls:
                    all_urls.add(u)
                    
            for url in all_urls:
                try:
                    items = await vinted_client.search(url)
                    if not items:
                        continue
                        
                    # Identifier les nouvelles annonces
                    if url not in known_items:
                        known_items[url] = []
                        # Au premier lancement, on sauvegarde tout pour ne pas spammer l'utilisateur
                        for item in items:
                            known_items[url].append(item['id'])
                        save_known_items(known_items)
                        continue
                        
                    new_items = []
                    for item in items:
                        if item['id'] not in known_items[url]:
                            new_items.append(item)
                            known_items[url].append(item['id'])
                    
                    if new_items:
                        # On garde seulement les 100 derniers IDs pour eviter que le fichier ne grossisse a l'infini
                        known_items[url] = known_items[url][-100:]
                        save_known_items(known_items)
                        
                        # Phase 4 : Envoi d'un message texte basique (sera ameliore en Phase 5 avec Embeds)
                        for user_id_str, user_urls in config_surveillances.items():
                            if url in user_urls:
                                user = self.get_user(int(user_id_str))
                                if user:
                                    for item in new_items:
                                        msg = (
                                            f"Nouvelle annonce trouvee !\n"
                                            f"Titre: {item.get('title', 'Inconnu')}\n"
                                            f"Prix: {item.get('price', {}).get('amount', 'Inconnu')} {item.get('price', {}).get('currency_code', '')}\n"
                                            f"Lien: {item.get('url', 'Inconnu')}"
                                        )
                                        try:
                                            await user.send(msg)
                                        except Exception as e:
                                            print(f"Impossible d'envoyer le MP a {user.name}: {e}")
                except Exception as e:
                    print(f"Erreur lors de la verification de l'URL {url}: {e}")

bot = VintedBot()

@bot.event
async def on_ready():
    print(f"Bot connecte en tant que {bot.user}")

@bot.tree.command(name="ping", description="Verifie si le bot VintedBot est en ligne")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! Le sniper Vinted est pret a tirer.", ephemeral=True)

@bot.tree.command(name="vinted_add", description="Ajoute une recherche Vinted a surveiller via son URL")
@app_commands.describe(url="L'URL de ta recherche (ex: https://www.vinted.fr/catalog?...)")
async def vinted_add(interaction: discord.Interaction, url: str):
    user_id = str(interaction.user.id)
    
    if "vinted." not in url:
        await interaction.response.send_message("L'URL ne semble pas etre une URL Vinted valide.", ephemeral=True)
        return
        
    if user_id not in config_surveillances:
        config_surveillances[user_id] = []
        
    if url in config_surveillances[user_id]:
        await interaction.response.send_message("Tu surveilles deja cette recherche !", ephemeral=True)
        return
        
    config_surveillances[user_id].append(url)
    save_config(config_surveillances)
    
    await interaction.response.send_message(
        f"**Surveillance Vinted ajoutee avec succes !**\n"
        f"Je te previendrai en MP des qu'une nouvelle annonce correspondant a ces criteres sera publiee.\n\n"
        f"*URL surveillee : <{url}>*", 
        ephemeral=True
    )

@bot.tree.command(name="vinted_list", description="Affiche la liste de tes surveillances Vinted actives")
async def vinted_list(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    urls = config_surveillances.get(user_id, [])
    
    if not urls:
        await interaction.response.send_message("Tu n'as aucune surveillance Vinted active pour le moment. Utilise `/vinted_add`.", ephemeral=True)
        return
        
    msg = "**Tes surveillances Vinted actives :**\n\n"
    for i, url in enumerate(urls, 1):
        msg += f"**{i}.** <{url}>\n"
        
    await interaction.response.send_message(msg, ephemeral=True)

async def autocomplete_vinted_urls(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    user_id = str(interaction.user.id)
    urls = config_surveillances.get(user_id, [])
    matches = [u for u in urls if current.lower() in u.lower()]
    return [app_commands.Choice(name=u[:100] + ("..." if len(u) > 100 else ""), value=u) for u in matches][:25]

@bot.tree.command(name="vinted_remove", description="Supprime une de tes surveillances Vinted")
@app_commands.describe(url="Choisis l'URL de la surveillance a supprimer")
@app_commands.autocomplete(url=autocomplete_vinted_urls)
async def vinted_remove(interaction: discord.Interaction, url: str):
    user_id = str(interaction.user.id)
    urls = config_surveillances.get(user_id, [])
    
    if url in urls:
        urls.remove(url)
        save_config(config_surveillances)
        await interaction.response.send_message("**Surveillance supprimee avec succes.** Je ne chercherai plus cette URL.", ephemeral=True)
    else:
        await interaction.response.send_message("Cette URL n'est pas dans ta liste de surveillances.", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("Erreur: DISCORD_BOT_TOKEN manquant dans le fichier .env")
    else:
        bot.run(TOKEN)
