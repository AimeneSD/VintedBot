import os
import aiomysql
import json
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "mysql-aimene.alwaysdata.net")
DB_USER = os.getenv("DB_USER", "aimene")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "aimene_vinted")

async def get_pool():
    if not hasattr(get_pool, "pool") or get_pool.pool is None:
        get_pool.pool = await aiomysql.create_pool(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            autocommit=True,
            pool_recycle=3600
        )
    return get_pool.pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Table pour éviter les doublons d'envoi discord
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS vinted_items (
                    id VARCHAR(255) PRIMARY KEY,
                    title TEXT,
                    price VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Table pour les configurations de surveillances
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS surveillances (
                    user_id VARCHAR(255),
                    url TEXT,
                    UNIQUE KEY user_url (user_id, url(255))
                )
            ''')
            # Table pour le cache des urls pour le sniper
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS cache_vinted (
                    url VARCHAR(767) PRIMARY KEY,
                    item_ids JSON
                )
            ''')

async def clean_old_vinted_items():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM vinted_items WHERE timestamp <= DATE_SUB(NOW(), INTERVAL 30 DAY)")

async def add_vinted_item(item_id: str, title: str, price: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT IGNORE INTO vinted_items (id, title, price) VALUES (%s, %s, %s)",
                (item_id, title, price)
            )

async def load_config():
    pool = await get_pool()
    config = {}
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT user_id, url FROM surveillances")
            rows = await cur.fetchall()
            for row in rows:
                uid = row["user_id"]
                url = row["url"]
                if uid not in config:
                    config[uid] = []
                config[uid].append(url)
    return config

async def save_config(config):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Pour faire simple on clear la table et on reinstert (car petite config)
            await cur.execute("TRUNCATE TABLE surveillances")
            for uid, urls in config.items():
                for url in urls:
                    await cur.execute(
                        "INSERT IGNORE INTO surveillances (user_id, url) VALUES (%s, %s)",
                        (uid, url)
                    )

async def load_known_items():
    pool = await get_pool()
    cache = {}
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT url, item_ids FROM cache_vinted")
            rows = await cur.fetchall()
            for row in rows:
                cache[row["url"]] = json.loads(row["item_ids"])
    return cache

async def save_known_items(cache):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for url, item_ids in cache.items():
                ids_json = json.dumps(item_ids)
                await cur.execute(
                    "INSERT INTO cache_vinted (url, item_ids) VALUES (%s, %s) ON DUPLICATE KEY UPDATE item_ids=VALUES(item_ids)",
                    (url, ids_json)
                )


# --- STUBS POUR EVITER LES CRASHS (A implémenter plus tard si besoin) ---
def get_average_vinted_price(keywords):
    return None

def get_all_component_prices():
    return None
