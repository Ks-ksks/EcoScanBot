import psycopg2
from psycopg2 import pool
from typing import Dict
from config import config

class Database:
    def __init__(self):
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(1, 10, host=config.db_host, port=config.db_port, database=config.db_name, user=config.db_user, password=config.db_password, sslmode='require')
            self._load_data()
        except Exception as e:
            print(f"Ошибка подключения к БД: {e}")
            self.pool = None
            self.store_prods = {}
            self.products = {}

    def _load_data(self):
        if not self.pool:
            return
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""SELECT name, matched_product_id FROM lenta WHERE name IS NOT NULL
                    UNION ALL SELECT name, matched_product_id FROM magnit WHERE name IS NOT NULL
                    UNION ALL SELECT name, matched_product_id FROM okey WHERE name IS NOT NULL
                    UNION ALL SELECT name, matched_product_id FROM perekrestok WHERE name IS NOT NULL
                    UNION ALL SELECT name, matched_product_id FROM x5 WHERE name IS NOT NULL""")
                self.store_prods = {}
                for name, matched_id in cursor.fetchall():
                    if name and len(name) > 3:
                        self.store_prods[name.lower()] = matched_id

                cursor.execute("""SELECT pr.id, pr.name, c.name as category, pr.carbon_footprint 
                    FROM product_reference pr JOIN categories c ON pr.category_id = c.id""")
                self.products = {}
                for product_id, name, category, footprint in cursor.fetchall():
                    self.products[product_id] = {'name': name, 'category': category, 'co2': float(footprint) if footprint else 0.0}
        finally:
            self.pool.putconn(conn)

    def get_store_products(self):
        return self.store_prods

    def get_product_info(self):
        return self.products

    def reload_data(self):
        self._load_data()

db = Database()