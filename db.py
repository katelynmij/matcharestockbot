import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def add_product(name, url, in_stock=False):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO products (name, url, in_stock, last_checked)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """, (name, url, in_stock, datetime.now()))
    product_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return product_id

def update_stock(product_id, in_stock):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE products
        SET in_stock=%s, last_checked=%s
        WHERE id=%s;
    """, (in_stock, datetime.now(), product_id))
    conn.commit()
    cur.close()
    conn.close()

def get_products():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, url, in_stock, last_checked FROM products;")
    products = cur.fetchall()
    cur.close()
    conn.close()
    return products
