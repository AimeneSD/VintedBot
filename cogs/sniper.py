import discord
from discord.ext import commands
import asyncio
import random
import utils.gemini as gemini
from utils.vinted import vinted_client
from utils.config import load_config, load_known_items, save_known_items
import utils.database as db

class VintedItemView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__()
        self.add_item(discord.ui.Button(label="Acheter sur Vinted", url=url, style=discord.ButtonStyle.link))

class SniperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.known_items = load_known_items()
        self.loop_task = bot.loop.create_task(self.vinted_sniper_loop())

    def cog_unload(self):
        self.loop_task.cancel()

    async def vinted_sniper_loop(self):
        await self.bot.wait_until_ready()
        print("Démarrage de la boucle de surveillance Vinted Phase 6 (Ultra-Rapide)...")
        while not self.bot.is_closed():
            delay = random.uniform(5, 8)
            await asyncio.sleep(delay)
            
            config_surveillances = load_config()
            all_urls = set()
            for urls in config_surveillances.values():
                for u in urls:
                    all_urls.add(u)
                    
            for url in all_urls:
                try:
                    items = await vinted_client.search(url)
                    if not items:
                        continue
                        
                    if url not in self.known_items:
                        self.known_items[url] = []
                        for item in items:
                            self.known_items[url].append(item['id'])
                        save_known_items(self.known_items)
                        continue
                        
                    new_items = []
                    for item in items:
                        if item['id'] not in self.known_items[url]:
                            new_items.append(item)
                            self.known_items[url].append(item['id'])
                    
                    if new_items:
                        self.known_items[url] = self.known_items[url][-100:]
                        save_known_items(self.known_items)
                        
                        for item in new_items:
                            self.bot.loop.create_task(self.process_item_async(item, url))
                            
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
                
            status = item.get("status", "Inconnu")
            item_data = {
                "title": title,
                "description": description_raw,
                "price": f"{price} {currency}",
                "condition": status
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
            
            color = discord.Color.green() if "FONCE" in recommandation else discord.Color.orange()
            
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
        config_surveillances = load_config()
        for user_id_str, user_urls in config_surveillances.items():
            if search_url in user_urls:
                try:
                    user = await self.bot.fetch_user(int(user_id_str))
                    if user:
                        await user.send(embeds=embeds)
                        await asyncio.sleep(1)
                except Exception as err:
                    print(f"Impossible d'envoyer a {user_id_str}: {err}")

async def setup(bot):
    await bot.add_cog(SniperCog(bot))
