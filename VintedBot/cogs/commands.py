import discord
from discord.ext import commands
from discord import app_commands
import os
import utils.database as db

async def autocomplete_vinted_urls(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    config_surveillances = await db.load_config()
    user_id = str(interaction.user.id)
    items = config_surveillances.get(user_id, [])
    
    matches = []
    for i, item in enumerate(items):
        u = item["url"]
        is_act = item.get("is_active", True)
        if current.lower() in u.lower():
            matches.append((str(i), u, is_act))
            
    choices = []
    for index_str, url, is_act in matches[:25]:
        status = "🟢" if is_act else "🔴"
        short_name = f"{int(index_str)+1}. {status} {url}"
        if len(short_name) > 100:
            short_name = short_name[:97] + "..."
        choices.append(app_commands.Choice(name=short_name, value=index_str))
    return choices

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Vérifie si le bot VintedBot est en ligne")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong! Le sniper Vinted est prêt à tirer.", ephemeral=True)

    @app_commands.command(name="vinted_add", description="Ajoute une recherche Vinted à surveiller via son URL")
    @app_commands.describe(url="L'URL de ta recherche (ex: https://www.vinted.fr/catalog?...)")
    async def vinted_add(self, interaction: discord.Interaction, url: str):
        config_surveillances = await db.load_config()
        user_id = str(interaction.user.id)
        
        if "vinted." not in url:
            await interaction.response.send_message("L'URL ne semble pas être une URL Vinted valide.", ephemeral=True)
            return

        if "order=newest_first" not in url:
            await interaction.response.send_message("❌ L'URL doit obligatoirement être triée par 'Articles récents' ! (ajoute le filtre 'Tri: Les plus récents' sur Vinted avant de copier le lien).", ephemeral=True)
            return
            
        if user_id not in config_surveillances:
            config_surveillances[user_id] = []
            
        if any(i["url"] == url for i in config_surveillances[user_id]):
            await interaction.response.send_message("Tu surveilles déjà cette recherche !", ephemeral=True)
            return
            
        config_surveillances[user_id].append({"url": url, "is_active": True})
        await db.save_config(config_surveillances)
        
        await interaction.response.send_message(
            f"**Surveillance Vinted ajoutée avec succès !**\n"
            f"Je te préviendrai en MP dès qu'une nouvelle annonce correspondant à ces critères sera publiée.\n\n"
            f"*URL surveillée : <{url}>*", 
            ephemeral=True
        )

    @app_commands.command(name="vinted_list", description="Affiche la liste de tes surveillances Vinted actives")
    async def vinted_list(self, interaction: discord.Interaction):
        config_surveillances = await db.load_config()
        user_id = str(interaction.user.id)
        items = config_surveillances.get(user_id, [])
        
        if not items:
            await interaction.response.send_message("Tu n'as aucune surveillance Vinted pour le moment. Utilise `/vinted_add`.", ephemeral=True)
            return
            
        msg = "**Tes surveillances Vinted :**\n\n"
        for i, item in enumerate(items, 1):
            status = "🟢 ACTIF" if item.get("is_active", True) else "🔴 INACTIF"
            msg += f"**{i}.** {status} <{item['url']}>\n"
            
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="vinted_remove", description="Supprime une de tes surveillances Vinted")
    @app_commands.describe(url_index="Choisis l'URL de la surveillance à supprimer dans la liste")
    @app_commands.autocomplete(url_index=autocomplete_vinted_urls)
    async def vinted_remove(self, interaction: discord.Interaction, url_index: str):
        config_surveillances = await db.load_config()
        user_id = str(interaction.user.id)
        items = config_surveillances.get(user_id, [])
        
        try:
            index = int(url_index)
            if 0 <= index < len(items):
                removed_item = items.pop(index)
                await db.save_config(config_surveillances)
                await interaction.response.send_message(f"**Surveillance supprimée avec succès.**\nURL retirée : <{removed_item['url']}>", ephemeral=True)
            else:
                await interaction.response.send_message("L'index fourni est invalide.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Sélection invalide.", ephemeral=True)

    @app_commands.command(name="vinted_toggle", description="Active ou désactive une surveillance Vinted")
    @app_commands.describe(url_index="Choisis l'URL de la surveillance à basculer")
    @app_commands.autocomplete(url_index=autocomplete_vinted_urls)
    async def vinted_toggle(self, interaction: discord.Interaction, url_index: str):
        config_surveillances = await db.load_config()
        user_id = str(interaction.user.id)
        items = config_surveillances.get(user_id, [])
        
        try:
            index = int(url_index)
            if 0 <= index < len(items):
                current_state = items[index].get("is_active", True)
                items[index]["is_active"] = not current_state
                await db.save_config(config_surveillances)
                new_status = "🟢 ACTIF" if not current_state else "🔴 INACTIF"
                await interaction.response.send_message(f"**Surveillance mise à jour.**\nLe lien est maintenant {new_status} :\n<{items[index]['url']}>", ephemeral=True)
            else:
                await interaction.response.send_message("L'index fourni est invalide.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Sélection invalide.", ephemeral=True)

    @app_commands.command(name="setprompt", description="Met à jour le fichier critere.md")
    @app_commands.describe(fichier="Fichier .md ou .txt contenant tes critères")
    async def setprompt(self, interaction: discord.Interaction, fichier: discord.Attachment):
        if not fichier.filename.endswith((".md", ".txt")):
            await interaction.response.send_message("Merci de fournir un fichier avec l'extension .md ou .txt", ephemeral=True)
            return
            
        await fichier.save("critere.md")
        await interaction.response.send_message("Fichier `critere.md` mis à jour avec succès !", ephemeral=True)

    @app_commands.command(name="getprompt", description="Affiche le prompt IA (critere.md)")
    async def getprompt(self, interaction: discord.Interaction):
        if os.path.exists("critere.md"):
            await interaction.response.send_message("Voici le prompt actuellement injecté à l'IA :", file=discord.File("critere.md"), ephemeral=True)
        else:
            await interaction.response.send_message("Aucun prompt n'est défini.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
