import pymysql
from pymysql.cursors import DictCursor

from citologia.config import ConexionBD


def abrir_conexion(c: ConexionBD, *, autocommit: bool = False):
    return pymysql.connect(
        host=c.host, port=c.port, user=c.user, password=c.password, database=c.name,
        charset="utf8mb4", cursorclass=DictCursor, connect_timeout=5, read_timeout=15,
        autocommit=autocommit)