from aiohttp import web
import os

async def handle_ping(request):
    return web.Response(text="Bot Vinted est en ligne et fonctionnel !")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    
    # Render donne le port via la variable d'environnement PORT, sinon 8080 par défaut
    port = int(os.environ.get('PORT', 8080))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    print(f"[Keep-Alive] Serveur web démarré sur le port {port} (pour Render)")
    await site.start()
