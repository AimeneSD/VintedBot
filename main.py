import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
import random
from dotenv import load_dotenv
from utils.vinted import vinted_client
import utils.gemini as gemini
import utils.database as db
import utils.keep_alive as keep_alive
from discord.ext import tasks

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CONFIG_FILE = "data/config_vinted.json"
CACHE_FILE = "data/offres_connues.json"

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

class VintedItemView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label="Acheter sur Vinted", url=url, style=discord.ButtonStyle.link))

class VintedBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.tree.sync()
        print("Commandes Slash synchronisées globalement")
        self.loop.create_task(self.vinted_sniper_loop())

    async def vinted_sniper_loop(self):
        await self.wait_until_ready()
        print("Démarrage de la boucle de surveillance Vinted Phase 6 (Ultra-Rapide)...")
        while not self.is_closed():
            delay = random.uniform(5, 8)
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
                            self.loop.create_task(self.process_item_async(item, url))
                            
                except Exception as e:
                    print(f"Erreur lors de la verification de l'URL {url}: {e}")

    async def process_item_async(self, item, search_url):
        try:
            item_id = str(item["id"])
            description_raw = await vinted_client.get_item_description(item_id)
            
            user_id = item.get("user", {}).get("id")
            seller_name = item.get("user", {}).get("login", "Inconnu")
            seller_rating_str = ""
            
            if user_id:
                user_info = await vinted_client.get_user_info(str(user_id))
                raw_rating = user_info.get("feedback_reputation", 0.0)
                count = user_info.get("feedback_count", 0)
                if count > 0:
                    rating = raw_rating * 5.0
                    seller_rating_str = f"Note : {rating:.1f}/5 ({count} avis)"
                else:
                    seller_rating_str = "Aucun avis"
            
            title = item.get("title", "Sans titre")
            price = item.get("price", {}).get("amount", "N/A")
            currency = item.get("price", {}).get("currency_code", "EUR")
            item_url = item.get("url", "https://www.vinted.fr")
            db.add_vinted_item(item_id, title, f"{price} {currency}")
            brand = item.get("brand_title", "")
            photo_url = ""
            if "photo" in item and item["photo"]:
                photo_url = item["photo"].get("url", "")
                
            item_data = {
                "title": title,
                "description": description_raw,
                "price": f"{price} {currency}"
            }
            
            analysis = await gemini.analyze_item_async(item_data)
            
            if analysis is None:
                return
            if not analysis.get("is_semantic_match", True):
                print(f"[Filtre] Match Sémantique = False pour {item_url}")
                return
            
            recommandation = analysis.get("recommandation", "À FUIR")
            if recommandation == "À FUIR":
                print(f"[Filtre] Recommandation À FUIR pour {item_url}")
                return
            
            score = analysis.get("confidence_score", 0)
            embed_title = f"{recommandation} | Score : {score}/100"
            
            color = discord.Color.green() if "" in recommandation else discord.Color.orange()
            
            main_embed = discord.Embed(
                title=embed_title,
                url=item_url,
                description=title,
                color=color
            )
            
            main_embed.add_field(name="Prix", value=f"**{price} {currency}**", inline=True)
            if brand:
                main_embed.add_field(name="Marque", value=brand, inline=True)
                
            financials = analysis.get("financial_estimation", {})
            profit = financials.get("estimated_net_profit_euros", "N/A")
            main_embed.add_field(name="Bénéfice net estimé", value=f"**+{profit}€**", inline=True)
            
            red_flags = analysis.get("red_flags", [])
            green_flags = analysis.get("green_flags", [])
            
            if green_flags:
                main_embed.add_field(name="Points Positifs", value="\n".join([f"- {f}" for f in green_flags]), inline=False)
            if red_flags:
                main_embed.add_field(name="Points Négatifs", value="\n".join([f"- {f}" for f in red_flags]), inline=False)
                
            repairs = analysis.get("repairs_needed", [])
            if repairs:
                main_embed.add_field(name="Réparations", value="\n".join([f"- {f}" for f in repairs]), inline=False)
            
            if seller_name:
                footer_text = f"Vendeur : {seller_name}"
                if seller_rating_str:
                    footer_text += f" - {seller_rating_str}"
                main_embed.set_footer(text=footer_text)
            
            if photo_url:
                main_embed.set_image(url=photo_url)
            
            await self.send_to_subscribers(search_url, [main_embed])
            
        except Exception as e:
            print(f"Erreur process_item_async: {e}")

    async def send_to_subscribers(self, search_url, embeds):
        for user_id_str, user_urls in config_surveillances.items():
            if search_url in user_urls:
                try:
                    user = await self.fetch_user(int(user_id_str))
                    if user:
                        await user.send(embeds=embeds)
                        await asyncio.sleep(1)
                except Exception as err:
                    print(f"Impossible d'envoyer a {user_id_str}: {err}")

bot = VintedBot()

@bot.event
async def on_ready():
    db.init_db()
    db.clean_old_vinted_items()
    
    # Lancement du serveur web pour Render
    bot.loop.create_task(keep_alive.start_server())

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

@bot.tree.command(name="setprompt", description="Met à jour le fichier critere.md (Ton filtre IA personnalisé)")
@app_commands.describe(fichier="Fichier .md ou .txt contenant tes critères")
async def setprompt(interaction: discord.Interaction, fichier: discord.Attachment):
    if not fichier.filename.endswith((".md", ".txt")):
        await interaction.response.send_message("Merci de fournir un fichier avec l'extension .md ou .txt", ephemeral=True)
        return
        
    await fichier.save("critere.md")
    await interaction.response.send_message("Fichier `critere.md` mis à jour avec succès ! L'IA utilisera ce nouveau prompt à partir de maintenant.", ephemeral=True)

@bot.tree.command(name="getprompt", description="Affiche le prompt IA (critere.md) actuellement utilisé par le bot")
async def getprompt(interaction: discord.Interaction):
    import os
    if os.path.exists("critere.md"):
        await interaction.response.send_message("Voici le prompt actuellement injecté à l'IA :", file=discord.File("critere.md"), ephemeral=True)
    else:
        await interaction.response.send_message("Aucun prompt personnalisé n'est défini (le fichier critere.md est introuvable).", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("Erreur: DISCORD_BOT_TOKEN manquant dans le fichier .env")
    else:
        bot.run(TOKEN)


