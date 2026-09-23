import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.storage import VILLES_FILE, charger_json
import utils.database as db
import utils.crypto as crypto
from utils.crous import (
    RAYON_DEFAULT_KM,
    obtenir_coordonnees,
    chercher_crous,
    verifier_session,
    renouveler_session_automatiquement,
)
from utils.discord_embed import creer_embed_logement
from utils.keep_alive import start_web_server
# --- CONFIGURATION ---
TOKEN_BOT_DISCORD = os.getenv("TOKEN_BOT_DISCORD")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))

# Chargement du cache persistant
villes_crous = charger_json(VILLES_FILE, [])

import unicodedata

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower()

async def autocomplete_villes(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Auto-complétion dynamique des villes CROUS pour les commandes slash"""
    if not current:
        return [app_commands.Choice(name=v, value=v) for v in villes_crous[:25]]
    
    current_norm = normalize_text(current)
    
    matches = []
    for v in villes_crous:
        v_norm = normalize_text(v)
        if current_norm in v_norm:
            matches.append(app_commands.Choice(name=v, value=v))
            if len(matches) >= 25:
                break
                
    return matches[:25]

# Initialisation du Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)



# --- BOUCLE AUTOMATIQUE 24/7 ---

@tasks.loop(seconds=CHECK_INTERVAL)
async def boucle_surveillance_automatique():
    """Vérifie en arrière-plan les nouvelles offres pour les utilisateurs enregistrés"""
    surveillances_dict = await db.load_surveillances()
    if not surveillances_dict:
        return

    offres_connues = await db.load_offres_connues()

    for author_id_str, liste_surveillances in list(surveillances_dict.items()):
        if not liste_surveillances:
            continue
            
        user_offres_connues = offres_connues.get(author_id_str, set())
            
        phpsessid = await db.get_session(author_id_str)

        is_valid = await asyncio.to_thread(verifier_session, phpsessid) if phpsessid else False
        
        if is_valid is None:
            print(f"[Session] Erreur réseau temporaire pour {author_id_str}. On ignore ce cycle.")
            continue
            
        if not is_valid:
            user_creds = await db.get_credentials(author_id_str)
            nouveau_phpsessid = None
            if user_creds:
                email = user_creds.get('email')
                password_chiffre = user_creds.get('password')
                password = crypto.dechiffrer(password_chiffre)
                print(f"[Session] Renouvellement automatique pour {author_id_str}...")
                nouveau_phpsessid = await asyncio.to_thread(renouveler_session_automatiquement, email, password)
                
            if nouveau_phpsessid:
                await db.save_session(author_id_str, nouveau_phpsessid)
                phpsessid = nouveau_phpsessid
            else:
                if phpsessid:
                    print(f"[Session] La session de l'utilisateur {author_id_str} a expiré et le renouvellement automatique a échoué.")
                    try:
                        user = await bot.fetch_user(int(author_id_str))
                        if user:
                            await user.send("Ta session CROUS (cookie `PHPSESSID`) a expiré ou est invalide, et le renouvellement automatique a échoué. Pense à utiliser la commande `/login` ou `/setcookie` en attendant !")
                    except Exception as e:
                        print(f"Impossible d'envoyer un MP à l'utilisateur {author_id_str} : {e}")
                    
                    await db.delete_session(author_id_str)
                continue 

        target = None
        try:
            target = await bot.fetch_user(int(author_id_str))
        except Exception as e:
            print(f"[Auto] Erreur lors de la récupération de l'utilisateur {author_id_str} : {e}")

        for info in liste_surveillances:
            nom_officiel = info.get("ville")
            rayon_km = info.get("rayon_km", RAYON_DEFAULT_KM)
            lat, lon, nom_officiel, bbox = obtenir_coordonnees(nom_officiel)

            if not lat or not lon:
                continue

            try:
                items = await asyncio.to_thread(chercher_crous, lat, lon, rayon_km=rayon_km, bbox=bbox, phpsessid=phpsessid)
                nouveaux_items = []
                for item in items:
                    logement_id = item.get('id')
                    if logement_id and logement_id not in user_offres_connues:
                        await db.add_offre_connue(author_id_str, logement_id)
                        user_offres_connues.add(logement_id)
                        print(f"[Auto] Nouvelle offre détectée pour {nom_officiel} ({rayon_km}km) - ID: {logement_id}")
                        nouveaux_items.append(item)
                        
                if nouveaux_items:
                    if bbox and rayon_km == RAYON_DEFAULT_KM:
                        msg_content = f"**{len(nouveaux_items)} nouvelle(s) offre(s) de logement à {nom_officiel} !**"
                    else:
                        msg_content = f"**{len(nouveaux_items)} nouvelle(s) offre(s) de logement (périmètre {rayon_km} km autour de {nom_officiel}) !**"
                        
                    embeds_list = [creer_embed_logement(item, ville_recherchee=nom_officiel if rayon_km == RAYON_DEFAULT_KM else f"{nom_officiel} ({rayon_km}km)") for item in nouveaux_items]
                    
                    for i in range(0, len(embeds_list), 10):
                        chunk = embeds_list[i:i+10]
                        if target:
                            try:
                                await target.send(content=msg_content if i == 0 else None, embeds=chunk)
                            except discord.Forbidden:
                                pass
                        
                        if i + 10 < len(embeds_list):
                            await asyncio.sleep(1)
            except Exception as e:
                print(f"Erreur surveillance {nom_officiel} pour {author_id_str}: {e}")
@boucle_surveillance_automatique.before_loop
async def avant_boucle():
    await bot.wait_until_ready()


# --- ÉVÉNEMENTS & COMMANDES DISCORD ---
@bot.event
async def on_ready():
    await db.init_db()
    if not hasattr(bot, 'web_server_started'):
        # bot.loop.create_task(start_web_server())
        bot.web_server_started = True
    print(f"Bot connecté en tant que {bot.user.name}")
    try:
        # Nettoyage des commandes locales pour éviter les doublons (conformément à l'architecture)
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            
        # Synchronisation globale
        synced = await bot.tree.sync()
        print(f"Commandes Slash synchronisées globalement : {len(synced)}")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes Slash : {e}")
        
    if not boucle_surveillance_automatique.is_running():
        boucle_surveillance_automatique.start()
        print(f"Boucle de surveillance démarrée (périmètre par défaut: {RAYON_DEFAULT_KM} km)")


@bot.tree.command(name="crous", description="Recherche des logements CROUS")
@app_commands.guild_only()
@app_commands.describe(
    ville="La ville où tu cherches un logement (ex: Paris)",
    rayon_km="Optionnel : Chercher dans un rayon X autour de la ville."
)
@app_commands.autocomplete(ville=autocomplete_villes)

async def commande_crous(interaction: discord.Interaction, ville: str, rayon_km: int = RAYON_DEFAULT_KM):
    await interaction.response.defer(ephemeral=True) # Réponse invisible pour les autres utilisateurs
    phpsessid = await db.get_session(str(interaction.user.id))

    is_valid = await asyncio.to_thread(verifier_session, phpsessid) if phpsessid else False
    if is_valid is None:
        await interaction.followup.send("Une erreur réseau avec le CROUS empêche la vérification de ta session. Réessaie dans quelques instants.", ephemeral=True)
        return
        
    if not is_valid:
        user_creds = await db.get_credentials(str(interaction.user.id))
        if user_creds:
            email = user_creds.get('email')
            password_chiffre = user_creds.get('password')
            password = crypto.dechiffrer(password_chiffre)
            phpsessid = await asyncio.to_thread(renouveler_session_automatiquement, email, password)
            if phpsessid:
                await db.save_session(str(interaction.user.id), phpsessid)
                
        if not phpsessid:
            await db.delete_session(str(interaction.user.id))
            await interaction.followup.send("Ta session est invalide et le renouvellement automatique a échoué. Utilise `/login` ou `/setcookie`.", ephemeral=True)
            return

    lat, lon, nom_officiel, bbox = obtenir_coordonnees(ville)
    if lat is None:
        await interaction.followup.send(f"Impossible de trouver la ville **{ville}**.")
        return
        
    items = await asyncio.to_thread(chercher_crous, lat, lon, rayon_km=rayon_km, bbox=bbox, phpsessid=phpsessid)
    if not items:
        if bbox and rayon_km == RAYON_DEFAULT_KM:
            await interaction.followup.send(f"Aucun logement CROUS trouvé actuellement à **{nom_officiel}**.")
        else:
            await interaction.followup.send(f"Aucun logement CROUS trouvé actuellement dans un rayon de **{rayon_km} km** autour de **{nom_officiel}**.")
        return
    
    if bbox and rayon_km == RAYON_DEFAULT_KM:
        msg_summary = f"**{len(items)}** logement(s) trouvé(s) à **{nom_officiel}** :"
    else:
        msg_summary = f"**{len(items)}** logement(s) trouvé(s) (rayon de **{rayon_km} km** autour de **{nom_officiel}**) :"
        
    embeds_list = [creer_embed_logement(item, ville_recherchee=nom_officiel) for item in items]
    
    try:
        await interaction.user.send(msg_summary)
        for i in range(0, len(embeds_list), 10):
            chunk = embeds_list[i:i+10]
            await interaction.user.send(embeds=chunk)
            if i + 10 < len(embeds_list):
                await asyncio.sleep(1)
        await interaction.followup.send("Les résultats t'ont été envoyés en message privé.")
    except discord.Forbidden:
        await interaction.followup.send("Impossible de t'envoyer un message privé. Voici les résultats ici :\\n" + msg_summary)
        for i in range(0, len(embeds_list), 10):
            chunk = embeds_list[i:i+10]
            await interaction.followup.send(embeds=chunk)
            if i + 10 < len(embeds_list):
                await asyncio.sleep(1)


@bot.tree.command(name="surveiller", description="Active la surveillance (cumulable)")
@app_commands.guild_only()
@app_commands.describe(
    ville="La ville à surveiller (ex: Lyon)",
    rayon_km="Optionnel : Le rayon de surveillance."
)
@app_commands.autocomplete(ville=autocomplete_villes)

async def commande_surveiller(interaction: discord.Interaction, ville: str, rayon_km: int = RAYON_DEFAULT_KM):
    await interaction.response.defer(ephemeral=True)
    author_id_str = str(interaction.user.id)
    phpsessid = await db.get_session(author_id_str)

    is_valid = await asyncio.to_thread(verifier_session, phpsessid) if phpsessid else False
    if is_valid is None:
        await interaction.followup.send("Une erreur réseau avec le CROUS empêche la vérification de ta session. Réessaie dans quelques instants.", ephemeral=True)
        return
        
    if not is_valid:
        user_creds = await db.get_credentials(author_id_str)
        if user_creds:
            email = user_creds.get('email')
            password_chiffre = user_creds.get('password')
            password = crypto.dechiffrer(password_chiffre)
            phpsessid = await asyncio.to_thread(renouveler_session_automatiquement, email, password)
            if phpsessid:
                await db.save_session(author_id_str, phpsessid)
                
        if not phpsessid:
            await db.delete_session(author_id_str)
            await interaction.followup.send("Ta session est invalide et le renouvellement automatique a échoué. Utilise `/login` ou `/setcookie`.", ephemeral=True)
            return

    lat, lon, nom_officiel, bbox = obtenir_coordonnees(ville)
    
    if lat is None:
        await interaction.followup.send(f"Impossible de trouver la ville **{ville}**.", ephemeral=True)
        return

    surveillances = await db.load_surveillances()
    user_list = surveillances.get(author_id_str, [])
    
    if len(user_list) >= 1:
        await interaction.followup.send("⚠️ Tu ne peux surveiller qu'**une seule ville à la fois**. Utilise `/stop_surveillance` pour supprimer ta ville actuelle avant d'en ajouter une autre.", ephemeral=True)
        return
        
    for s in user_list:
        if s.get("ville") == nom_officiel:
            await interaction.followup.send(f"Tu surveilles déjà **{nom_officiel}** !", ephemeral=True)
            return

    await db.add_surveillance(author_id_str, nom_officiel, rayon_km)

    if bbox and rayon_km == RAYON_DEFAULT_KM:
        await interaction.followup.send(f"**Surveillance ajoutée**, le bot vérifiera les logements toutes les {CHECK_INTERVAL}s à **{nom_officiel}**.", ephemeral=True)
    else:
        await interaction.followup.send(f"**Surveillance ajoutée**, le bot vérifiera les logements toutes les {CHECK_INTERVAL}s dans un périmètre de **{rayon_km} km** autour de **{nom_officiel}**.", ephemeral=True)

    # === ENVOI IMMÉDIAT DES OFFRES EXISTANTES ===
    try:
        items = await asyncio.to_thread(chercher_crous, lat, lon, rayon_km=rayon_km, bbox=bbox, phpsessid=phpsessid)
        nouveaux_items = []
        offres_connues = await db.load_offres_connues()
        user_offres_connues = offres_connues.get(author_id_str, set())
        for item in items:
            logement_id = item.get('id')
            if logement_id:
                if logement_id not in user_offres_connues:
                    await db.add_offre_connue(author_id_str, logement_id)
                    nouveaux_items.append(item)
                
        if nouveaux_items:
            msg_content = f"**{len(nouveaux_items)} offre(s) actuellement disponible(s) pour ta nouvelle surveillance à {nom_officiel} !**"
            
            ville_str = nom_officiel if rayon_km == RAYON_DEFAULT_KM else f"{nom_officiel} ({rayon_km}km)"
            embeds_list = [creer_embed_logement(item, ville_recherchee=ville_str) for item in nouveaux_items]
            
            for i in range(0, len(embeds_list), 10):
                chunk = embeds_list[i:i+10]
                try:
                    await interaction.user.send(content=msg_content if i == 0 else None, embeds=chunk)
                except discord.Forbidden:
                    channel = bot.get_channel(int(interaction.channel_id))
                    if channel:
                        await channel.send(content=msg_content if i == 0 else None, embeds=chunk)
                if i + 10 < len(embeds_list):
                    await asyncio.sleep(1)
    except Exception as e:
        print(f"Erreur lors de la recherche initiale pour {nom_officiel}: {e}")

@bot.tree.command(name="stop_surveillance", description="Arrête une ou toutes tes surveillances")
@app_commands.guild_only()
@app_commands.describe(ville="Laisse vide pour tout arrêter, ou tape le nom de la ville")
@app_commands.autocomplete(ville=autocomplete_villes)

async def commande_stop_surveillance(interaction: discord.Interaction, ville: str = None):
    author_id_str = str(interaction.user.id)
    surveillances = await db.load_surveillances()
    user_list = surveillances.get(author_id_str, [])
    
    if not user_list:
        await interaction.response.send_message("Tu n'as aucune surveillance active en ce moment.", ephemeral=True)
        return

    if ville:
        lat, lon, nom_officiel, bbox = obtenir_coordonnees(ville)
        target_name = nom_officiel if lat else ville
        
        has_surv = any(s.get("ville") == target_name for s in user_list)
        if not has_surv:
            await interaction.response.send_message(f"Tu ne surveilles pas la ville de **{target_name}**.", ephemeral=True)
            return
        
        await db.remove_surveillance(author_id_str, target_name)
        await interaction.response.send_message(f"Surveillance arrêtée pour **{target_name}**.", ephemeral=True)
    else:
        await db.remove_surveillance(author_id_str)
        await interaction.response.send_message("Toutes tes surveillances ont été arrêtées.", ephemeral=True)


@bot.tree.command(name="mes_surveillances", description="Affiche la liste de tes surveillances actives")
@app_commands.guild_only()

async def commande_mes_surveillances(interaction: discord.Interaction):
    author_id_str = str(interaction.user.id)
    surveillances = await db.load_surveillances()
    user_list = surveillances.get(author_id_str, [])

    if not user_list:
        await interaction.response.send_message("Tu n'as aucune surveillance active en ce moment.", ephemeral=True)
        return

    lignes = []
    for info in user_list:
        nom_officiel = info.get("ville", "Inconnue")
        rayon_km = info.get("rayon_km", RAYON_DEFAULT_KM)
        if rayon_km == RAYON_DEFAULT_KM:
            lieu = f"**{nom_officiel}**"
        else:
            lieu = f"**{nom_officiel}** (rayon de {rayon_km} km)"
        lignes.append(f"- {lieu}")
    msg = "Voici tes surveillances actives (utilise `/stop_surveillance` pour en annuler une) :\\n" + "\\n".join(lignes)
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="setcookie", description="Enregistre ton cookie PHPSESSID pour que le bot cherche en ton nom.")
@app_commands.guild_only()
@app_commands.describe(cookie_val="La valeur de ton PHPSESSID")

async def commande_setcookie(interaction: discord.Interaction, cookie_val: str):
    await db.save_session(str(interaction.user.id), cookie_val)
    await interaction.response.send_message("Ton cookie de session a été enregistré et sécurisé ! Personne d'autre ne peut voir ce message.", ephemeral=True)


@bot.tree.command(name="login", description="Enregistre tes identifiants pour le renouvellement automatique de ta session.")
@app_commands.guild_only()
@app_commands.describe(email="Ton adresse email CROUS", password="Ton mot de passe CROUS")

async def commande_login(interaction: discord.Interaction, email: str, password: str):
    await interaction.response.defer(ephemeral=True)
    
    phpsessid = await asyncio.to_thread(renouveler_session_automatiquement, email, password)
    
    if phpsessid:
        await db.save_session(str(interaction.user.id), phpsessid)
        await db.save_credentials(str(interaction.user.id), email, crypto.chiffrer(password))
        
        await interaction.followup.send("Connexion réussie ! Tes identifiants ont été sauvegardés en sécurité et ta session est active.")
    else:
        await interaction.followup.send("Échec de la connexion. Vérifie tes identifiants ou essaie `/setcookie` si le problème persiste.")


@bot.tree.command(name="logout", description="Déconnecte-toi et supprime tes identifiants de la mémoire du bot.")
@app_commands.guild_only()

async def commande_logout(interaction: discord.Interaction):
    user_id_str = str(interaction.user.id)
    
    sess = await db.get_session(user_id_str)
    cred = await db.get_credentials(user_id_str)
    
    if sess or cred:
        await db.delete_session(user_id_str)
        await db.delete_credentials(user_id_str)
        await interaction.response.send_message("Tu as bien été déconnecté. Tes identifiants et ta session ont été supprimés de la mémoire !", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'étais pas connecté.", ephemeral=True)

def start():
    print("Démarrage du bot Discord...")
    bot.run(TOKEN_BOT_DISCORD)

if __name__ == "__main__":
    start()
