import sqlite3
from concurrent.futures import ThreadPoolExecutor

from citologia.db.estado import SqliteNotificacionRepository as Repo

S, T = "a" * 64, "ACTIVACION_COLPOSCOPIA"


def test_reservar_una_sola_vez(tmp_path):
    r = Repo(tmp_path / "e.db")
    assert r.reservar(S, T) is True
    assert r.reservar(S, T) is False


def test_persiste_entre_instancias(tmp_path):
    Repo(tmp_path / "e.db").reservar(S, T)
    assert Repo(tmp_path / "e.db").reservar(S, T) is False


def test_enviado_no_se_vuelve_a_reservar(tmp_path):
    r = Repo(tmp_path / "e.db")
    r.reservar(S, T)
    r.marcar_enviado(S, T, "<id>")
    assert r.reservar(S, T) is False


def test_error_se_reintenta_hasta_el_limite(tmp_path):
    r = Repo(tmp_path / "e.db", max_intentos=2)
    assert r.reservar(S, T)
    r.marcar_error(S, T, "EmailError")
    assert r.reservar(S, T)          # intento 2
    r.marcar_error(S, T, "EmailError")
    assert not r.reservar(S, T)      # límite alcanzado


def test_enviando_atascado_pasa_a_revision_manual(tmp_path):
    ruta = tmp_path / "e.db"
    r = Repo(ruta)
    r.reservar(S, T)
    assert r.marcar_atascados(15) == 0          # recién creado: no está atascado
    c = sqlite3.connect(ruta)
    c.execute("UPDATE notificacion SET actualizado_en = datetime('now', '-1 hour')")
    c.commit(); c.close()
    assert r.marcar_atascados(15) == 1
    assert r.reservar(S, T) is False            # no se reenvía solo


def test_concurrencia_solo_uno_gana(tmp_path):
    r = Repo(tmp_path / "e.db")
    with ThreadPoolExecutor(8) as ex:
        resultados = list(ex.map(lambda _: r.reservar(S, T), range(8)))
    assert resultados.count(True) == 1