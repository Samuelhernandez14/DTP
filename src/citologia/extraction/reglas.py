"""Paso previo al LLM: resuelve con expresiones regulares los informes que usan
frases estándar del sistema Bethesda. Instantáneo, determinista y auditable.
Solo los casos que NO resuelve con claridad pasan al modelo de IA."""

import re
import unicodedata

from citologia.domain.catalogo import VPH_DETECTADO, VPH_NO_DETECTADO

_ACENTOS = str.maketrans("áéíóúüñ", "aeiouun")


def _norm(texto: str) -> str:
    """Minúsculas sin tildes. Conserva la LONGITUD del texto (1 carácter -> 1 carácter),
    lo que permite mapear coincidencias al texto original."""
    minus = "".join(c.lower() if len(c.lower()) == 1 else c for c in texto)
    return minus.translate(_ACENTOS)


_LEI = r"(?:lei|lesion\s+intraepitelial(?:\s+escamosa)?)"
_PATRONES = [
    (13, r"adenocarcinoma\s+endocervical\s+in\s+situ"),
    (14, r"adenocarcinoma\s+endocervical"),
    (15, r"adenocarcinoma\s+endometrial"),
    (6,  r"carcinoma\s+(?:de\s+celulas\s+)?escamos[ao]s?|carcinoma\s+escamocelular"),
    (5,  _LEI + r"\s+de\s+alto\s+grado[^.\n]{0,40}(?:sospech|infiltra)"
              r"|sospech\w+\s+de\s+(?:infiltracion|invasion)"),
    (4,  _LEI + r"\s+de\s+alto\s+grado|\bh-?sil\b|\bnic\s*(?:ii|iii|2|3)\b|\bcarcinoma\s+in\s+situ"),
    (3,  _LEI + r"\s+de\s+bajo\s+grado|\bl-?sil\b|\bnic\s*(?:i|1)\b"),
    (2,  r"\basc-?\s?h\b"),
    (1,  r"\basc-?\s?us\b|significado\s+indeterminado"),
    (10, r"celulas\s+endocervicales\s+atipicas[^.\n]{0,40}sospech"),
    (11, r"celulas\s+endometriales\s+atipicas[^.\n]{0,40}sospech"),
    (12, r"celulas\s+glandulares\s+atipicas[^.\n]{0,40}sospech"),
    (7,  r"celulas\s+endocervicales\s+atipicas"),
    (8,  r"celulas\s+endometriales\s+atipicas"),
    (9,  r"celulas\s+glandulares\s+atipicas|\bagc\b"),
    (16, r"otras\s+neoplasias"),
    (17, r"negativ[oa]\s+para\s+(?:la\s+)?(?:lesion\s+intraepitelial|malignidad)"),
    (18, r"inadecuad[ao]\s+para\s+(?:la\s+)?(?:lectura|evaluacion)|\binsatisfactori[ao]"
         r"|muestra\s+rechazada"),
]
_PATRONES = [(c, re.compile(p)) for c, p in _PATRONES]

_NEGACION = re.compile(
    r"\b(?:no\s+se\s+(?:observan?|identifican?|evidencian?|encontraron|hallaron)"
    r"|sin\s+evidencia\s+de|ausencia\s+de|no\s+hay|se\s+descarta)\b[^.\n]{0,30}$"
)

_INICIO = ("calidad de la muestra", "clasificacion general", "interpretacion")
_FIN = ("recomendaciones", "firma", "el resultado emitido")

_ANEXO1 = re.compile(
    r"anexo\s*(?:no\.?\s*)?1\b|orden\s+medica\s+de\s+colposcopia"
    r"|remision\s+a\s+colposcopia|solicitud\s+de\s+colposcopia"
)


def recortar_seccion(texto: str) -> tuple[str, bool]:
    n = _norm(texto)
    inicios = [i for i in (n.find(m) for m in _INICIO) if i != -1]
    if not inicios:
        return texto, False
    ini = min(inicios)
    fines = [i for i in (n.find(m, ini) for m in _FIN) if i != -1]
    fin = min(fines) if fines else len(texto)
    return texto[ini:fin], True


def _detectar_vph(n: str):
    detectado = no_detectado = False
    for m in re.finditer(r"\b(?:vph|hpv|pvh|virus\s+del\s+papiloma)\b([^\n]{0,60})", n):
        resto = m.group(1)
        if re.search(r"no\s+detectad|negativ", resto):
            no_detectado = True
        elif re.search(r"detectad|positiv", resto):
            detectado = True
    if detectado and not no_detectado:
        return VPH_DETECTADO
    if no_detectado and not detectado:
        return VPH_NO_DETECTADO
    return None


def extraer_por_reglas(texto: str) -> dict:
    # NFC una sola vez a la entrada: tildes descompuestas (o + ´) no romperían
    # los patrones y la alineación de índices se mantiene.
    texto = unicodedata.normalize("NFC", texto)
    recorte, encontrada = recortar_seccion(texto)
    trabajo = list(_norm(recorte))
    codigos, evidencias, alertas = set(), [], []

    for codigo, patron in _PATRONES:
        s = "".join(trabajo)
        for m in patron.finditer(s):
            ventana = s[max(0, m.start() - 60):m.start()]
            if codigo != 17 and _NEGACION.search(ventana):
                alertas.append(f"Hallazgo negado en el texto (código {codigo})")
            else:
                codigos.add(codigo)
                evidencias.append(" ".join(recorte[m.start():m.end()].split()))
            for k in range(m.start(), m.end()):
                trabajo[k] = " "

    if len(codigos - {17, 18}) >= 3:
        alertas.append("Tres o más hallazgos distintos: posible plantilla con todas las opciones")
    if {17, 18} <= codigos:
        alertas.append("Aparecen 'negativa' e 'inadecuada' a la vez")
    if not encontrada:
        alertas.append("No se ubicó la sección de resultado")

    n_total = _norm(texto)
    claro = encontrada and bool(codigos) and not alertas
    return {
        "codigos_citologia": sorted(codigos),
        "vph": _detectar_vph(n_total),
        "tiene_anexo1": bool(_ANEXO1.search(n_total)),
        "evidencia": " | ".join(evidencias),
        "confianza": 0.95 if claro else (0.5 if codigos else 0.0),
        "errores_validacion": [],
        "claro": claro,
        "alertas": alertas,
        "seccion_encontrada": encontrada,
        "texto_recortado": recorte,
    }
