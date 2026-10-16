import sqlite3
from contextlib import closing
from pathlib import Path

from citologia.domain.errors import DatabaseError

_DDL = """
CREATE TABLE IF NOT EXISTS notificacion (
  documento_sha256 TEXT NOT NULL,
  tipo TEXT NOT NULL,
  estado TEXT NOT NULL CHECK (estado IN ('ENVIANDO','ENVIADO','ERROR','REVISION_MANUAL')),
  intentos INTEGER NOT NULL DEFAULT 1,
  message_id TEXT,
  codigo_error TEXT,
  creado_en TEXT NOT NULL DEFAULT (datetime('now')),
  actualizado_en TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (documento_sha256, tipo)
) WITHOUT ROWID
"""
_INSERT = "INSERT INTO notificacion (documento_sha256, tipo, estado) VALUES (?, ?, 'ENVIANDO')"
_RECLAMAR_ERROR = ("UPDATE notificacion SET estado='ENVIANDO', intentos=intentos+1, "
                   "actualizado_en=datetime('now') "
                   "WHERE documento_sha256=? AND tipo=? AND estado='ERROR' AND intentos < ?")
_ENVIADO = ("UPDATE notificacion SET estado='ENVIADO', message_id=?, actualizado_en=datetime('now') "
            "WHERE documento_sha256=? AND tipo=? AND estado='ENVIANDO'")
_ERROR = ("UPDATE notificacion SET estado='ERROR', codigo_error=?, actualizado_en=datetime('now') "
          "WHERE documento_sha256=? AND tipo=? AND estado='ENVIANDO'")
_ATASCADOS = ("UPDATE notificacion SET estado='REVISION_MANUAL', actualizado_en=datetime('now') "
              "WHERE estado='ENVIANDO' AND actualizado_en < datetime('now', ?)")


class SqliteNotificacionRepository:
    def __init__(self, ruta: Path, max_intentos: int = 3):
        self._ruta, self._max = Path(ruta), max_intentos
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        self._ejecutar("PRAGMA journal_mode=WAL", ())
        self._ejecutar(_DDL, ())

    def _ejecutar(self, sql: str, params: tuple) -> int:
        try:
            with closing(sqlite3.connect(self._ruta, timeout=10, isolation_level=None)) as c:
                return c.execute(sql, params).rowcount
        except sqlite3.IntegrityError:
            raise
        except sqlite3.Error as e:
            raise DatabaseError(f"Fallo en estado local: {type(e).__name__}") from e

    def reservar(self, sha256: str, tipo: str) -> bool:
        """True solo para quien gana el candado y debe enviar."""
        try:
            self._ejecutar(_INSERT, (sha256, tipo))
            return True
        except sqlite3.IntegrityError:      # ya existe la fila
            return self._ejecutar(_RECLAMAR_ERROR, (sha256, tipo, self._max)) == 1

    def marcar_enviado(self, sha256: str, tipo: str, message_id: str) -> None:
        self._ejecutar(_ENVIADO, (message_id, sha256, tipo))

    def marcar_error(self, sha256: str, tipo: str, codigo: str) -> None:
        self._ejecutar(_ERROR, (codigo, sha256, tipo))

    def marcar_atascados(self, minutos: int = 15) -> int:
        """Los 'ENVIANDO' viejos (caída entre enviar y marcar) pasan a revisión manual."""
        return self._ejecutar(_ATASCADOS, (f"-{int(minutos)} minutes",))