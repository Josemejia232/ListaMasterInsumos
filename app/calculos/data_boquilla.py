BOQUILLA_DATA: dict[str, dict[int, float]] = {
    "10x10x0.9": {2: 0.65, 3: 0.97, 4: 1.30, 5: 1.62},
    "20x20x0.9": {2: 0.32, 3: 0.49, 4: 0.65, 5: 0.81},
    "30x30x0.9": {2: 0.22, 3: 0.32, 4: 0.43, 5: 0.54},
    "30x60x0.9": {2: 0.16, 3: 0.24, 4: 0.32, 5: 0.41},
    "40x40x0.9": {2: 0.16, 3: 0.24, 4: 0.32, 5: 0.41},
}

PRECIO_BOQUILLA_KG: float = 18000.0

PRECIOS_BOQUILLA: dict[str, float] = {
    "Boquilla (polvo)": PRECIO_BOQUILLA_KG,
    "M.O. Boquilla": 12000.0,
}

FORMATOS = list(BOQUILLA_DATA.keys())
ANCHOS_DISPONIBLES = sorted({mm for v in BOQUILLA_DATA.values() for mm in v})


def calcular_boquilla(formato: str, ancho_mm: int, area_m2: float) -> dict:
    if formato not in BOQUILLA_DATA:
        raise ValueError(f"Formato '{formato}' no valido. Usar: {', '.join(FORMATOS)}")
    if ancho_mm not in BOQUILLA_DATA[formato]:
        raise ValueError(f"Ancho {ancho_mm}mm no valido para formato {formato}. Usar: {ANCHOS_DISPONIBLES}")
    if area_m2 <= 0:
        raise ValueError("Area debe ser mayor a 0")

    factor = BOQUILLA_DATA[formato][ancho_mm]
    kg_totales = round(factor * area_m2, 2)

    precio_boquilla = PRECIOS_BOQUILLA["Boquilla (polvo)"]
    precio_mo = PRECIOS_BOQUILLA["M.O. Boquilla"]

    materiales = [
        {"nombre": "Boquilla (polvo)", "unidad": "kg", "cantidad": kg_totales, "vr_unitario": precio_boquilla},
        {"nombre": "M.O. Boquilla", "unidad": "m²", "cantidad": area_m2, "vr_unitario": precio_mo},
    ]

    for m in materiales:
        m["vr_total"] = round(m["cantidad"] * m["vr_unitario"], 2)

    total = round(sum(m["vr_total"] for m in materiales), 2)

    return {
        "formato": formato,
        "ancho_mm": ancho_mm,
        "area_m2": area_m2,
        "factor_consumo": factor,
        "kg_totales": kg_totales,
        "materiales": materiales,
        "total": total,
    }
