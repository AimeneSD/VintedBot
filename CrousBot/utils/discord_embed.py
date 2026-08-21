import discord

def creer_embed_logement(item, ville_recherchee=None):
    """Génère un Embed Discord attractif pour une offre de logement CROUS"""
    logement_id = item.get('id')
    type_logement = item.get('label', 'Logement CROUS')
    residence = item.get('residence', {}).get('label', 'Résidence Inconnue')
    adresse = item.get('residence', {}).get('address', 'Adresse non renseignée')
    surface = item.get('area', {}).get('min', 'N/C')
    
    # Extraction et mise en forme propre des équipements
    equipements_raw = item.get('equipments', [])
    labels = []
    if isinstance(equipements_raw, list):
        for eq in equipements_raw:
            if isinstance(eq, dict) and eq.get('label'):
                labels.append(eq.get('label'))
            elif isinstance(eq, str):
                labels.append(eq)
    
    equipements_texte = ", ".join(labels) if labels else "Non renseignés"
    
    loyer_centimes = item.get('occupationModes', [{}])[0].get('rent', {}).get('min', 0)
    loyer_euros = f"{loyer_centimes / 100:.2f} €" if loyer_centimes else "N/C"
    
    lien = f"https://trouverunlogement.lescrous.fr/tools/47/accommodations/{logement_id}"
    
    embed = discord.Embed(
        title=residence,
        url=lien,
        color=discord.Color.green()
    )
    if type_logement and type_logement != "Logement CROUS":
        embed.add_field(name="Type", value=type_logement, inline=False)
        
    embed.add_field(name="Loyer", value=loyer_euros, inline=True)
    embed.add_field(name="Surface", value=f"{surface} m²", inline=True)
    embed.add_field(name="Adresse", value=adresse, inline=False)
    embed.add_field(name="Équipements", value=equipements_texte, inline=False)
    
    footer_text = "Alerte CROUS Bot"
    if ville_recherchee:
        footer_text += f" • Périmètre autour de {ville_recherchee}"
    embed.set_footer(text=footer_text)
    
    return embed
