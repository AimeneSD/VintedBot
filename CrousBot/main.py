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

from utils.storage import CACHE_FILE, CONFIG_FILE, SESSIONS_FILE, VILLES_FILE, CREDENTIALS_FILE, charger_json, sauvegarder_json
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
_raw_cache = charger_json(CACHE_FILE, {})
if isinstance(_raw_cache, list):
    _raw_cache = {}
offres_connues = {str(k): set(v) for k, v in _raw_cache.items()}
config_surveillance = charger_json(CONFIG_FILE, {"channels": {}})
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
    surveillances_dict = config_surveillance.get("surveillances", {})
    if not surveillances_dict:
        return

    nouveaux_trouves = False
    sessions = charger_json(SESSIONS_FILE, {})

    for author_id_str, liste_surveillances in list(surveillances_dict.items()):
        if not liste_surveillances:
            continue
            
        user_offres_connues = offres_connues.setdefault(author_id_str, set())
            
        phpsessid = sessions.get(author_id_str)

        is_valid = await asyncio.to_thread(verifier_session, phpsessid) if phpsessid else False
        
        if is_valid is None:
            # Erreur réseau temporaire (429, 503, timeout). On ignore ce cycle sans supprimer la session.
            print(f"[Session] Erreur réseau temporaire pour {author_id_str}. On ignore ce cycle.")
            continue
            
        if not is_valid:
            credentials = charger_json(CREDENTIALS_FILE, {})
            user_creds = credentials.get(author_id_str)
            nouveau_phpsessid = None
            if user_creds:
                email = user_creds.get('email')
                password = user_creds.get('password')
                print(f"[Session] Renouvellement automatique pour {author_id_str}...")
                nouveau_phpsessid = await asyncio.to_thread(renouveler_session_automatiquement, email, password)
                
            if nouveau_phpsessid:
                sessions[author_id_str] = nouveau_phpsessid
                sauvegarder_json(SESSIONS_FILE, sessions)
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
                    
                    # Supprimer la session invalide
                    del sessions[author_id_str]
                    sauvegarder_json(SESSIONS_FILE, sessions)
                continue # On passe à l'utilisateur suivant

        target = None
        try:
            target = await bot.fetch_user(int(author_id_str))
        except Exception as e:
            print(f"[Auto] Erreur lors de la récupération de l'utilisateur {author_id_str} : {e}")

        for info in liste_surveillances:
            lat = info.get("lat")
            lon = info.get("lon")
            nom_officiel = info.get("ville")
            rayon_km = info.get("rayon", RAYON_DEFAULT_KM)
            bbox = info.get("bbox")
            channel_fallback_id = info.get("channel_id")

            if not lat or not lon:
                continue

            try:
                items = await asyncio.to_thread(chercher_crous, lat, lon, rayon_km=rayon_km, bbox=bbox, phpsessid=phpsessid)
                nouveaux_items = []
                for item in items:
                    logement_id = item.get('id')
                    if logement_id and logement_id not in user_offres_connues:
                        user_offres_connues.add(logement_id)
                        nouveaux_trouves = True
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
                        sent_to_dm = False
                        
                        if target:
                            try:
                                await target.send(content=msg_content if i == 0 else None, embeds=chunk)
                                sent_to_dm = True
                            except discord.Forbidden:
                                pass
                        
                        # Si l'utilisateur a bloqué les MP, envoi dans le salon de secours
                        if not sent_to_dm and channel_fallback_id:
                            channel = bot.get_channel(int(channel_fallback_id))
                            if channel:
                                await channel.send(content=msg_content if i == 0 else None, embeds=chunk)
                                
                        if i + 10 < len(embeds_list):
                            await asyncio.sleep(1)
            except Exception as e:
                print(f"Erreur surveillance {nom_officiel} pour {author_id_str}: {e}")

    if nouveaux_trouves:
        sauvegarder_json(CACHE_FILE, {k: list(v) for k, v in offres_connues.items()})

@boucle_surveillance_automatique.before_loop
async def avant_boucle():
    await bot.wait_until_ready()


# --- ÉVÉNEMENTS & COMMANDES DISCORD ---
def migrer_config_si_besoin():
    if "channels" in config_surveillance:
        print("[Migration] Conversion de l'ancienne structure 'channels' vers 'surveillances'...")
        new_surveillances = {}
        for ch_id, info in config_surveillance["channels"].items():
            author_id = info.get("author_id")
            if not author_id: continue
            
            surv = dict(info)
            surv["channel_id"] = ch_id
            
            if author_id not in new_surveillances:
                new_surveillances[author_id] = []
            new_surveillances[author_id].append(surv)
            
        config_surveillance["surveillances"] = new_surveillances
        del config_surveillance["channels"]
        sauvegarder_json(CONFIG_FILE, config_surveillance)
        print("[Migration] Terminée avec succès.")

@bot.event
async def on_ready():
    migrer_config_si_besoin()
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
@app_commands.describe(
    ville="La ville où tu cherches un logement (ex: Paris)",
    rayon_km="Optionnel : Chercher dans un rayon X autour de la ville."
)
@app_commands.autocomplete(ville=autocomplete_villes)
async def commande_crous(interaction: discord.Interaction, ville: str, rayon_km: int = RAYON_DEFAULT_KM):
    await interaction.response.defer(ephemeral=True) # Réponse invisible pour les autres utilisateurs
    sessions = charger_json(SESSIONS_FILE, {})
    phpsessid = sessions.get(str(interaction.user.id))

    is_valid = await asyncio.to_thread(verifier_session, phpsessid) if phpsessid else False
    if is_valid is None:
        await interaction.followup.send("Une erreur réseau avec le CROUS empêche la vérification de ta session. Réessaie dans quelques instants.", ephemeral=True)
        return
        
    if not is_valid:
        credentials = charger_json(CREDENTIALS_FILE, {})
        user_creds = credentials.get(str(interaction.user.id))
        if user_creds:
            email = user_creds.get('email')
            password = user_creds.get('password')
            phpsessid = await asyncio.to_thread(renouveler_session_automatiquement, email, password)
            if phpsessid:
                sessions[str(interaction.user.id)] = phpsessid
                sauvegarder_json(SESSIONS_FILE, sessions)
                
        if not phpsessid:
            if str(interaction.user.id) in sessions:
                del sessions[str(interaction.user.id)]
                sauvegarder_json(SESSIONS_FILE, sessions)
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
        await interaction.followup.send("Impossible de t'envoyer un message privé. Voici les résultats ici :\n" + msg_summary)
        for i in range(0, len(embeds_list), 10):
            chunk = embeds_list[i:i+10]
            await interaction.followup.send(embeds=chunk)
            if i + 10 < len(embeds_list):
                await asyncio.sleep(1)


@bot.tree.command(name="surveiller", description="Active la surveillance (cumulable)")
@app_commands.describe(
    ville="La ville à surveiller (ex: Lyon)",
    rayon_km="Optionnel : Le rayon de surveillance."
)
@app_commands.autocomplete(ville=autocomplete_villes)
async def commande_surveiller(interaction: discord.Interaction, ville: str, rayon_km: int = RAYON_DEFAULT_KM):
    await interaction.response.defer(ephemeral=True)
    sessions = charger_json(SESSIONS_FILE, {})
    phpsessid = sessions.get(str(interaction.user.id))

    is_valid = await asyncio.to_thread(verifier_session, phpsessid) if phpsessid else False
    if is_valid is None:
        await interaction.followup.send("Une erreur réseau avec le CROUS empêche la vérification de ta session. Réessaie dans quelques instants.", ephemeral=True)
        return
        
    if not is_valid:
        credentials = charger_json(CREDENTIALS_FILE, {})
        user_creds = credentials.get(str(interaction.user.id))
        if user_creds:
            email = user_creds.get('email')
            password = user_creds.get('password')
            phpsessid = await asyncio.to_thread(renouveler_session_automatiquement, email, password)
            if phpsessid:
                sessions[str(interaction.user.id)] = phpsessid
                sauvegarder_json(SESSIONS_FILE, sessions)
                
        if not phpsessid:
            if str(interaction.user.id) in sessions:
                del sessions[str(interaction.user.id)]
                sauvegarder_json(SESSIONS_FILE, sessions)
            await interaction.followup.send("Ta session est invalide et le renouvellement automatique a échoué. Utilise `/login` ou `/setcookie`.", ephemeral=True)
            return

    lat, lon, nom_officiel, bbox = obtenir_coordonnees(ville)
    
    if lat is None:
        await interaction.followup.send(f"Impossible de trouver la ville **{ville}**.", ephemeral=True)
        return

    author_id_str = str(interaction.user.id)
    surveillances = config_surveillance.setdefault("surveillances", {})
    user_list = surveillances.setdefault(author_id_str, [])
    
    # Vérifier si la ville est déjà surveillée par l'utilisateur
    for s in user_list:
        if s.get("ville") == nom_officiel:
            await interaction.followup.send(f"Tu surveilles déjà **{nom_officiel}** !", ephemeral=True)
            return

    user_list.append({
        "ville": nom_officiel,
        "lat": lat,
        "lon": lon,
        "rayon": rayon_km,
        "bbox": bbox,
        "channel_id": str(interaction.channel_id)
    })
    sauvegarder_json(CONFIG_FILE, config_surveillance)

    if bbox and rayon_km == RAYON_DEFAULT_KM:
        await interaction.followup.send(f"**Surveillance ajoutée**, le bot vérifiera les logements toutes les {CHECK_INTERVAL}s à **{nom_officiel}**.", ephemeral=True)
    else:
        await interaction.followup.send(f"**Surveillance ajoutée**, le bot vérifiera les logements toutes les {CHECK_INTERVAL}s dans un périmètre de **{rayon_km} km** autour de **{nom_officiel}**.", ephemeral=True)

    # === ENVOI IMMÉDIAT DES OFFRES EXISTANTES ===
    try:
        items = await asyncio.to_thread(chercher_crous, lat, lon, rayon_km=rayon_km, bbox=bbox, phpsessid=phpsessid)
        nouveaux_items = []
        user_offres_connues = offres_connues.setdefault(author_id_str, set())
        for item in items:
            logement_id = item.get('id')
            if logement_id:
                user_offres_connues.add(logement_id)
                nouveaux_items.append(item)
                
        if nouveaux_items:
            sauvegarder_json(CACHE_FILE, {k: list(v) for k, v in offres_connues.items()})
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
@app_commands.describe(ville="Laisse vide pour tout arrêter, ou tape le nom de la ville")
@app_commands.autocomplete(ville=autocomplete_villes)
async def commande_stop_surveillance(interaction: discord.Interaction, ville: str = None):
    author_id_str = str(interaction.user.id)
    surveillances = config_surveillance.get("surveillances", {})
    
    if author_id_str not in surveillances or not surveillances[author_id_str]:
        await interaction.response.send_message("Tu n'as aucune surveillance active en ce moment.", ephemeral=True)
        return

    user_list = surveillances[author_id_str]
    
    if ville:
        lat, lon, nom_officiel, bbox = obtenir_coordonnees(ville)
        target_name = nom_officiel if lat else ville
        
        new_list = [s for s in user_list if s.get("ville") != target_name]
        if len(new_list) == len(user_list):
            await interaction.response.send_message(f"Tu ne surveilles pas la ville de **{target_name}**.", ephemeral=True)
            return
        
        config_surveillance["surveillances"][author_id_str] = new_list
        sauvegarder_json(CONFIG_FILE, config_surveillance)
        await interaction.response.send_message(f"Surveillance arrêtée pour **{target_name}**.", ephemeral=True)
    else:
        del config_surveillance["surveillances"][author_id_str]
        sauvegarder_json(CONFIG_FILE, config_surveillance)
        await interaction.response.send_message("Toutes tes surveillances ont été arrêtées.", ephemeral=True)


@bot.tree.command(name="mes_surveillances", description="Affiche la liste de tes surveillances actives")
async def commande_mes_surveillances(interaction: discord.Interaction):
    author_id_str = str(interaction.user.id)
    user_list = config_surveillance.get("surveillances", {}).get(author_id_str, [])

    if not user_list:
        await interaction.response.send_message("Tu n'as aucune surveillance active en ce moment.", ephemeral=True)
        return

    lignes = []
    for info in user_list:
        nom_officiel = info.get("ville", "Inconnue")
        rayon_km = info.get("rayon", RAYON_DEFAULT_KM)
        bbox = info.get("bbox")
        if bbox and rayon_km == RAYON_DEFAULT_KM:
            lieu = f"**{nom_officiel}**"
        else:
            lieu = f"**{nom_officiel}** (rayon de {rayon_km} km)"
        lignes.append(f"- {lieu}")

    msg = "Voici tes surveillances actives (utilise `/stop_surveillance` pour en annuler une) :\n" + "\n".join(lignes)
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="setcookie", description="Enregistre ton cookie PHPSESSID pour que le bot cherche en ton nom.")
@app_commands.describe(cookie_val="La valeur de ton PHPSESSID")
async def commande_setcookie(interaction: discord.Interaction, cookie_val: str):
    sessions = charger_json(SESSIONS_FILE, {})
    sessions[str(interaction.user.id)] = cookie_val
    sauvegarder_json(SESSIONS_FILE, sessions)
    
    # Avec les Slash commands, on peut répondre de manière "ephemeral" (visible uniquement par l'utilisateur !)
    await interaction.response.send_message("Ton cookie de session a été enregistré et sécurisé ! Personne d'autre ne peut voir ce message.", ephemeral=True)


@bot.tree.command(name="login", description="Enregistre tes identifiants pour le renouvellement automatique de ta session.")
@app_commands.describe(email="Ton adresse email CROUS", password="Ton mot de passe CROUS")
async def commande_login(interaction: discord.Interaction, email: str, password: str):
    await interaction.response.defer(ephemeral=True)
    
    # Tentative de connexion immédiate
    phpsessid = await asyncio.to_thread(renouveler_session_automatiquement, email, password)
    
    if phpsessid:
        # Enregistrer la session
        sessions = charger_json(SESSIONS_FILE, {})
        sessions[str(interaction.user.id)] = phpsessid
        sauvegarder_json(SESSIONS_FILE, sessions)
        
        # Enregistrer les identifiants
        credentials = charger_json(CREDENTIALS_FILE, {})
        credentials[str(interaction.user.id)] = {
            "email": email,
            "password": password
        }
        sauvegarder_json(CREDENTIALS_FILE, credentials)
        
        await interaction.followup.send("Connexion réussie ! Tes identifiants ont été sauvegardés en sécurité et ta session est active.")
    else:
        await interaction.followup.send("Échec de la connexion. Vérifie tes identifiants ou essaie `/setcookie` si le problème persiste.")


@bot.tree.command(name="logout", description="Déconnecte-toi et supprime tes identifiants de la mémoire du bot.")
async def commande_logout(interaction: discord.Interaction):
    sessions = charger_json(SESSIONS_FILE, {})
    credentials = charger_json(CREDENTIALS_FILE, {})
    
    user_id_str = str(interaction.user.id)
    deleted = False
    
    if user_id_str in sessions:
        del sessions[user_id_str]
        sauvegarder_json(SESSIONS_FILE, sessions)
        deleted = True
        
    if user_id_str in credentials:
        del credentials[user_id_str]
        sauvegarder_json(CREDENTIALS_FILE, credentials)
        deleted = True
        
    if deleted:
        await interaction.response.send_message("Tu as bien été déconnecté. Tes identifiants et ta session ont été supprimés de la mémoire !", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'étais pas connecté.", ephemeral=True)

def start():
    print("Démarrage du bot Discord...")
    bot.run(TOKEN_BOT_DISCORD)

if __name__ == "__main__":
    start()
