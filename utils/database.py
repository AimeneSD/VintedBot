import sqlite3
import datetime
import os

DB_PATH = "market_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table pour l'historique Vinted (suppression des items > 3 semaines)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vinted_items (
            id TEXT PRIMARY KEY,
            title TEXT,
            price REAL,
            currency TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table pour les prix des composants (Aliexpress/Amazon)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS component_prices (
            component_name TEXT PRIMARY KEY,
            average_price REAL,
            source TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def clean_old_vinted_items():
    """Supprime les annonces de plus de 3 semaines (21 jours)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    three_weeks_ago = datetime.datetime.now() - datetime.timedelta(days=21)
    cursor.execute('DELETE FROM vinted_items WHERE timestamp < ?', (three_weeks_ago.strftime('%Y-%m-%d %H:%M:%S'),))
    conn.commit()
    conn.close()

def add_vinted_item(item_id, title, price_str):
    try:
        # Nettoyage du prix (ex: "15.0 EUR" -> 15.0)
        price_val = float(''.join(c for c in price_str.split()[0] if c.isdigit() or c == '.'))
        currency = price_str.split()[1] if len(price_str.split()) > 1 else "EUR"
    except:
        price_val = 0.0
        currency = "EUR"
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO vinted_items (id, title, price, currency, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (str(item_id), title, price_val, currency, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_average_vinted_price(keywords):
    """Calcule le prix moyen sur les annonces Vinted correspondantes"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Recherche naïve par mots clés (ex: "%ps5%")
    query = "SELECT AVG(price), COUNT(id) FROM vinted_items WHERE "
    conditions = []
    for kw in keywords.split():
        conditions.append("title LIKE ?")
    
    query += " AND ".join(conditions)
    params = [f"%{kw}%" for kw in keywords.split()]
    
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    
    if result and result[1] > 0:
        return {"avg_price": round(result[0], 2), "count": result[1]}
    return None

def add_component_price(name, price, source="IA"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO component_prices (component_name, average_price, source, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (name.lower(), price, source, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_all_component_prices():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    two_weeks_ago = datetime.datetime.now() - datetime.timedelta(days=14)
    cursor.execute('SELECT component_name, average_price FROM component_prices WHERE timestamp >= ?', (two_weeks_ago.strftime('%Y-%m-%d %H:%M:%S'),))
    results = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in results}
