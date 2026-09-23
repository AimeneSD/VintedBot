import os
import aiomysql
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "mysql-aimene.alwaysdata.net")
DB_USER = os.getenv("DB_USER", "aimene")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("CROUS_DB_NAME", "aimene_crous")

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
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS `crous_villes` (
                  `id` int(11) NOT NULL AUTO_INCREMENT,
                  `nom` varchar(255) NOT NULL,
                  PRIMARY KEY (`id`),
                  UNIQUE KEY `nom` (`nom`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            ''')
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS `crous_surveillances` (
                  `id` int(11) NOT NULL AUTO_INCREMENT,
                  `user_id` varchar(255) NOT NULL,
                  `ville` varchar(255) NOT NULL,
                  `rayon_km` int(11) NOT NULL DEFAULT 10,
                  `is_active` tinyint(1) NOT NULL DEFAULT 1,
                  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  KEY `user_id` (`user_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            ''')
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS `crous_offres_connues` (
                  `user_id` varchar(255) NOT NULL,
                  `offre_id` varchar(255) NOT NULL,
                  `discovered_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (`user_id`, `offre_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            ''')
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS `crous_sessions` (
                  `user_id` varchar(255) NOT NULL,
                  `phpsessid` varchar(255) NOT NULL,
                  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`user_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            ''')
            await cur.execute('''
                CREATE TABLE IF NOT EXISTS `crous_credentials` (
                  `user_id` varchar(255) NOT NULL,
                  `email` varchar(255) NOT NULL,
                  `password` varchar(255) NOT NULL,
                  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`user_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            ''')

# --- SURVEILLANCES ---
async def load_surveillances():
    """Retourne un dict: { user_id: [ {"ville": "...", "rayon_km": ...}, ... ] }"""
    pool = await get_pool()
    config = {}
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT user_id, ville, rayon_km FROM crous_surveillances WHERE is_active = 1")
            rows = await cur.fetchall()
            for row in rows:
                uid = str(row["user_id"])
                ville = row["ville"]
                rayon_km = row["rayon_km"]
                if uid not in config:
                    config[uid] = []
                config[uid].append({"ville": ville, "rayon_km": rayon_km})
    return config

async def add_surveillance(user_id: str, ville: str, rayon_km: int = 10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO crous_surveillances (user_id, ville, rayon_km, is_active) VALUES (%s, %s, %s, 1)",
                (user_id, ville, rayon_km)
            )

async def remove_surveillance(user_id: str, ville: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if ville:
                await cur.execute("DELETE FROM crous_surveillances WHERE user_id = %s AND ville = %s", (user_id, ville))
            else:
                await cur.execute("DELETE FROM crous_surveillances WHERE user_id = %s", (user_id,))

# --- OFFRES CONNUES ---
async def load_offres_connues():
    """Retourne un dict: { user_id: set([offre_id1, offre_id2, ...]) }"""
    pool = await get_pool()
    cache = {}
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # On ne garde que les offres découvertes il y a moins de 30 jours pour nettoyer
            await cur.execute("DELETE FROM crous_offres_connues WHERE discovered_at <= DATE_SUB(NOW(), INTERVAL 30 DAY)")
            await cur.execute("SELECT user_id, offre_id FROM crous_offres_connues")
            rows = await cur.fetchall()
            for row in rows:
                uid = str(row["user_id"])
                offre_id = row["offre_id"]
                if uid not in cache:
                    cache[uid] = set()
                cache[uid].add(offre_id)
    return cache

async def add_offre_connue(user_id: str, offre_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT IGNORE INTO crous_offres_connues (user_id, offre_id) VALUES (%s, %s)",
                (user_id, offre_id)
            )

# --- SESSIONS ---
async def get_session(user_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT phpsessid FROM crous_sessions WHERE user_id = %s", (user_id,))
            row = await cur.fetchone()
            if row:
                return row["phpsessid"]
    return None

async def save_session(user_id: str, phpsessid: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO crous_sessions (user_id, phpsessid) VALUES (%s, %s) ON DUPLICATE KEY UPDATE phpsessid=VALUES(phpsessid)",
                (user_id, phpsessid)
            )

async def delete_session(user_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM crous_sessions WHERE user_id = %s", (user_id,))

# --- CREDENTIALS ---
async def get_credentials(user_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT email, password FROM crous_credentials WHERE user_id = %s", (user_id,))
            row = await cur.fetchone()
            if row:
                return {"email": row["email"], "password": row["password"]}
    return None

async def save_credentials(user_id: str, email: str, password_chiffre: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO crous_credentials (user_id, email, password) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE email=VALUES(email), password=VALUES(password)",
                (user_id, email, password_chiffre)
            )

async def delete_credentials(user_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM crous_credentials WHERE user_id = %s", (user_id,))
