import pymysql
import os

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "youruser"),
        password=os.getenv("DB_PASS", "yourpass"),
        database=os.getenv("DB_NAME", "yourdb"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )