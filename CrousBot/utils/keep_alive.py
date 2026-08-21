from aiohttp import web
import asyncio
import os

async def health_check(request):
    """Renvoie une réponse 200 OK pour prouver que le bot est en vie."""
    return web.Response(text="OK 200")

async def start_web_server():
    """Démarre le serveur web aiohttp en arrière-plan."""
    app = web.Application()
    app.add_routes([
        web.get('/', health_check),
        web.get('/health', health_check)
    ])
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    try:
        await site.start()
        print(f"Serveur web Health API démarré sur le port {port} (UptimeRobot activé)")
    except OSError as e:
        if e.errno == 98:
            print(f"Le port {port} est déjà utilisé (le serveur est probablement déjà lancé).")
        else:
            raise
