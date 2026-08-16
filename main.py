import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
import random
from dotenv import load_dotenv
from utils.vinted import vinted_client
from deep_translator import GoogleTranslator

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

# --- Fonctions Utilitaires ---
def translate_to_fr(text):
    if not text:
        return ""
    try:
        return GoogleTranslator(source='auto', target='fr').translate(text)
    except Exception as e:
        print(f"Erreur traduction: {e}")
        return text

class VintedItemView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label="Acheter sur Vinted", url=url, style=discord.ButtonStyle.link))

# -----------------------------------

class VintedBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.tree.sync()
        print("Commandes Slash synchronisées globalement")
        self.loop.create_task(self.vinted_sniper_loop())

    async def vinted_sniper_loop(self):
        await self.wait_until_ready()
        print("Démarrage de la boucle de surveillance Vinted Phase 5...")
        while not self.is_closed():
            delay = random.uniform(20, 23)
            await asyncio.sleep(delay)
            
            all_urls = set()
            for urls in config_surveillances.values():
                for u in urls:
                    all_urls.add(u)
                    
            for url in all_urls:
                try:
                    items = await vinted_client.search(url)
                    if not items:
                        continue
                        
                    if url not in known_items:
                        known_items[url] = []
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
                        known_items[url] = known_items[url][-100:]
                        save_known_items(known_items)
                        
                        for item in new_items:
                            # 1. Recuperer les details complets
                            detailed_item = await vinted_client.get_item(str(item['id']))
                            
                            # Fusionner les donnees
                            title = item.get('title', 'Sans titre')
                            price = item.get('price', {}).get('amount', 'N/A')
                            currency = item.get('price', {}).get('currency_code', 'EUR')
                            item_url = item.get('url', 'https://www.vinted.fr')
                            brand = item.get('brand_title', 'Non spécifiée')
                            size = item.get('size_title', 'Non spécifiée')
                            
                            description = ""
                            seller_name = "Inconnu"
                            photos = []
                            
                            if detailed_item:
                                description = detailed_item.get('description', '')
                                seller_name = detailed_item.get('user', {}).get('login', 'Inconnu')
                                photos_data = detailed_item.get('photos', [])
                                photos = [p.get('url') for p in photos_data if p.get('url')]
                            else:
                                # Fallback si get_item echoue
                                if 'photo' in item and item['photo']:
                                    photos = [item['photo'].get('url')]
                            
                            # 2. Traduire
                            title_fr = await asyncio.to_thread(translate_to_fr, title)
                            desc_fr = await asyncio.to_thread(translate_to_fr, description)
                            
                            if len(desc_fr) > 1024:
                                desc_fr = desc_fr[:1020] + "..."
                            
                            # 3. Construire les Embeds (Galerie d'images)
                            embeds = []
                            
                            # Embed principal
                            main_embed = discord.Embed(
                                title=title_fr,
                                url=item_url,
                                description=desc_fr if desc_fr else "*Aucune description*",
                                color=discord.Color.from_rgb(9, 177, 186) # Cyan Vinted
                            )
                            main_embed.add_field(name="Prix", value=f"**{price} {currency}**", inline=True)
                            main_embed.add_field(name="Taille", value=f"`{size}`", inline=True)
                            main_embed.add_field(name="Marque", value=brand, inline=True)
                            main_embed.add_field(name="Vendeur", value=seller_name, inline=True)
                            
                            if photos:
                                main_embed.set_image(url=photos[0])
                            
                            embeds.append(main_embed)
                            
                            # Embeds supplementaires pour les images (jusqu'a 4 autres pour faire max 5 images)
                            for photo_url in photos[1:5]:
                                extra_embed = discord.Embed(url=item_url)
                                extra_embed.set_image(url=photo_url)
                                embeds.append(extra_embed)
                                
                            view = VintedItemView(item_url)
                            
                            # 4. Envoyer aux utilisateurs concernes
                            for user_id_str, user_urls in config_surveillances.items():
                                if url in user_urls:
                                    try:
                                        user = await self.fetch_user(int(user_id_str))
                                        if user:
                                            await user.send(embeds=embeds, view=view)
                                    except Exception as err:
                                        print(f"Impossible d'envoyer a {user_id_str}: {err}")
                except Exception as e:
                    print(f"Erreur lors de la verification de l'URL {url}: {e}")

bot = VintedBot()

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")

@bot.tree.command(name="ping", description="Vérifie si le bot VintedBot est en ligne")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! Le sniper Vinted est prêt à tirer.", ephemeral=True)

@bot.tree.command(name="vinted_add", description="Ajoute une recherche Vinted à surveiller via son URL")
@app_commands.describe(url="L'URL de ta recherche (ex: https://www.vinted.fr/catalog?...)")
async def vinted_add(interaction: discord.Interaction, url: str):
    user_id = str(interaction.user.id)
    
    if "vinted." not in url:
        await interaction.response.send_message("L'URL ne semble pas être une URL Vinted valide.", ephemeral=True)
        return
        
    if user_id not in config_surveillances:
        config_surveillances[user_id] = []
        
    if url in config_surveillances[user_id]:
        await interaction.response.send_message("Tu surveilles déjà cette recherche !", ephemeral=True)
        return
        
    config_surveillances[user_id].append(url)
    save_config(config_surveillances)
    
    await interaction.response.send_message(
        f"**Surveillance Vinted ajoutée avec succès !**\n"
        f"Je te préviendrai en MP dès qu'une nouvelle annonce correspondant à ces critères sera publiée.\n\n"
        f"*URL surveillée : <{url}>*", 
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
    matches = [(str(i), u) for i, u in enumerate(urls) if current.lower() in u.lower()]
    
    choices = []
    for index_str, url in matches[:25]:
        short_name = f"{int(index_str)+1}. {url}"
        if len(short_name) > 100:
            short_name = short_name[:97] + "..."
        choices.append(app_commands.Choice(name=short_name, value=index_str))
        
    return choices

@bot.tree.command(name="vinted_remove", description="Supprime une de tes surveillances Vinted")
@app_commands.describe(url_index="Choisis l'URL de la surveillance à supprimer dans la liste")
@app_commands.autocomplete(url_index=autocomplete_vinted_urls)
async def vinted_remove(interaction: discord.Interaction, url_index: str):
    user_id = str(interaction.user.id)
    urls = config_surveillances.get(user_id, [])
    
    try:
        index = int(url_index)
        if 0 <= index < len(urls):
            removed_url = urls.pop(index)
            save_config(config_surveillances)
            await interaction.response.send_message(f"**Surveillance supprimée avec succès.**\nURL retirée : <{removed_url}>", ephemeral=True)
        else:
            await interaction.response.send_message("L'index fourni est invalide.", ephemeral=True)
    except ValueError:
        if url_index in urls:
            urls.remove(url_index)
            save_config(config_surveillances)
            await interaction.response.send_message("**Surveillance supprimée avec succès.**", ephemeral=True)
        else:
            await interaction.response.send_message("Sélection invalide. Utilise la liste déroulante pour choisir l'URL à supprimer.", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("Erreur: DISCORD_BOT_TOKEN manquant dans le fichier .env")
    else:
        bot.run(TOKEN)
