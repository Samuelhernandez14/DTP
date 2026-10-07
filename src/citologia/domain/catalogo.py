"""Catálogo de la tabla de maestros DTP_RESULTADO_CITOLOGIA_ESCALA_BETHESDA.
Única fuente de verdad: la usan el motor de reglas, las reglas de texto y el prompt."""

CITOLOGIA = {
    1: "ASC-US (células escamosas atípicas de significado indeterminado)",
    2: "ASC-H (células escamosas atípicas, sugestivo de LEI de alto grado)",
    3: "LEI de bajo grado - HPV (NIC I)",
    4: "LEI de alto grado (NIC II-III CA in situ)",
    5: "LEI de alto grado sospechosa de infiltración",
    6: "Carcinoma de células escamosas",
    7: "Células endocervicales atípicas sin ningún otro significado",
    8: "Células endometriales atípicas sin ningún otro significado",
    9: "Células glandulares atípicas sin ningún otro significado",
    10: "Células endocervicales atípicas sospechosas de neoplasia",
    11: "Células endometriales atípicas sospechosas de neoplasia",
    12: "Células glandulares atípicas sospechosas de neoplasia",
    13: "Adenocarcinoma endocervical in situ",
    14: "Adenocarcinoma endocervical",
    15: "Adenocarcinoma endometrial",
    16: "Otras neoplasias",
    17: "Negativa para lesión intraepitelial o neoplasia",
    18: "Inadecuada para lectura",
}

VPH_DETECTADO = 19
VPH_NO_DETECTADO = 20

# Regla 1: cualquier categoría 2..16
ANORMALES_REGLA_1 = frozenset(range(2, 17))