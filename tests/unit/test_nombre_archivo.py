from datetime import datetime

import pytest

from citologia.domain.errors import InvalidDocumentError
from citologia.ingestion.nombre_archivo import parsear_nombre


def test_parsea_formato_esperado():
    n = parsear_nombre("CC1000000001_CCU_20261006120503.pdf")
    assert (n.tipo_documento, n.numero_documento, n.clase) == ("CC", "1000000001", "CCU")
    assert n.fecha == datetime(2026, 10, 6, 12, 5, 3)


@pytest.mark.parametrize("malo", ["foto.pdf", "CC123_CCU_2026.pdf",
                                  "CC123_CCU_20261340120503.pdf"])
def test_formato_invalido(malo):
    with pytest.raises(InvalidDocumentError):
        parsear_nombre(malo)