import psycopg2
from psycopg2 import extras

class Database:
    def __init__(self, host, port, dbname, user, password):
        self.connection = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        self.connection.autocommit = False

    def query(self, sql, params=None):
        try:
            with self.connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception:
            self.connection.rollback()
            raise

    def execute(self, sql, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                self.connection.commit()
                return cursor.rowcount
        except Exception:
            self.connection.rollback()
            raise

    def insert(self, sql, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                self.connection.commit()
                return cursor.fetchone()[0]
        except Exception:
            self.connection.rollback()
            raise

    def close(self):
        self.connection.close()