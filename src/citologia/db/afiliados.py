import pymysql
from pymysql.cursors import DictCursor
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from citologia.domain.errors import DatabaseError
from citologia.domain.models import Afiliado
from citologia.config import ConexionBD  
from citologia.db.conexion import abrir_conexion


# Lista explícita: NUNCA SELECT * (la tabla trae datos sensibles que no necesitamos)
_SQL = """
SELECT id, id_afiliado, mae_tipo_documento_codigo, numero_documento,
       primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
       fecha_nacimiento, genero, telefono_fijo, telefono_movil, email,
       direccion_residencia, barrio, mae_estado_afiliacion_valor,
       mae_regimen_valor, duplicado
FROM aseg_afiliados
WHERE numero_documento = %s AND mae_tipo_documento_codigo = %s
LIMIT 10
"""


def _bit(valor) -> bool:
    # pymysql devuelve bit(1) como bytes (b'\x00' / b'\x01')
    return valor in (b"\x01", 1, True)


class MySQLAfiliadoRepository:
    def __init__(self, conexion: ConexionBD):
        self._c = conexion

    @retry(retry=retry_if_exception_type(pymysql.err.OperationalError),
           stop=stop_after_attempt(3), wait=wait_exponential_jitter(multiplier=1, max=10),
           reraise=True)
    def _consultar(self, tipo: str, numero: str) -> list[dict]:
        s = self._s
        with abrir_conexion(self._c) as conn, conn.cursor() as cur:
            cur.execute(_SQL, (numero, tipo))
            return list(cur.fetchall())

    def buscar(self, tipo_documento: str, numero_documento: str) -> list[Afiliado]:
        try:
            filas = self._consultar(tipo_documento, numero_documento)
        except pymysql.MySQLError as e:
            raise DatabaseError(f"Fallo consultando aseg_afiliados: {type(e).__name__}") from e
        return [Afiliado(
            id=f["id"], id_afiliado=f["id_afiliado"],
            tipo_documento=f["mae_tipo_documento_codigo"],
            numero_documento=f["numero_documento"],
            primer_nombre=f["primer_nombre"], segundo_nombre=f["segundo_nombre"],
            primer_apellido=f["primer_apellido"], segundo_apellido=f["segundo_apellido"],
            fecha_nacimiento=f["fecha_nacimiento"], genero=f["genero"],
            telefono_fijo=f["telefono_fijo"], telefono_movil=f["telefono_movil"],
            email=f["email"], direccion_residencia=f["direccion_residencia"],
            barrio=f["barrio"], estado_afiliacion=f["mae_estado_afiliacion_valor"],
            regimen=f["mae_regimen_valor"], duplicado=_bit(f["duplicado"]),
        ) for f in filas]