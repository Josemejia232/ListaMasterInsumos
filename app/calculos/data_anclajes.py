import math

PRECIOS_ANCLAJES: dict[str, float] = {
    "Sika AnchorFix 300ml": 45000.0,
    "Kit de Limpieza": 25000.0,
    "Tuercas y Arandelas": 2000.0,
    "M.O. Anclajes": 8000.0,
}

PRECIOS_VARILLA: dict[int, float] = {
    6: 3500.0,
    8: 5000.0,
    10: 8000.0,
    12: 12000.0,
    14: 16000.0,
    16: 20000.0,
    18: 25000.0,
    20: 30000.0,
    22: 35000.0,
    25: 42000.0,
    28: 50000.0,
    30: 55000.0,
    32: 60000.0,
}

PRECIOS_BROCA: dict[int, float] = {
    8: 12000.0,
    10: 15000.0,
    12: 18000.0,
    14: 20000.0,
    16: 25000.0,
    18: 28000.0,
    20: 32000.0,
    22: 35000.0,
    24: 38000.0,
    27: 42000.0,
    30: 45000.0,
    32: 48000.0,
    34: 50000.0,
}

FACTOR_ABSORCION = {
    "concreto": 1.0,
    "ladrillo_macizo": 1.15,
    "piedra": 1.05,
}


def calcular_anclaje(
    diametro_mm: int,
    profundidad_mm: int,
    cantidad: int,
    material_base: str = "concreto",
) -> dict:
    # Conversión a cm
    d_cm = diametro_mm / 10.0
    h_cm = profundidad_mm / 10.0

    # Volumen de 1 agujero en cm³
    vol_agujero = math.pi * (d_cm / 2) ** 2 * h_cm

    # Factor de absorción según material base
    factor = FACTOR_ABSORCION.get(material_base, 1.0)

    # Volumen total con desperdicio (20%) y factor de absorción
    vol_total = vol_agujero * cantidad * 1.20 * factor

    # Tubos de 300ml (redondeo hacia arriba)
    tubos = math.ceil(vol_total / 300.0)

    # Diámetro de broca = diámetro varilla + 2mm
    diametro_broca = diametro_mm + 2

    # Precios
    precio_varilla = PRECIOS_VARILLA.get(diametro_mm, 10000.0)
    precio_broca = PRECIOS_BROCA.get(diametro_broca, 20000.0)
    precio_sika = PRECIOS_ANCLAJES["Sika AnchorFix 300ml"]
    precio_tuercas = PRECIOS_ANCLAJES["Tuercas y Arandelas"]
    precio_limpieza = PRECIOS_ANCLAJES["Kit de Limpieza"]
    precio_mo = PRECIOS_ANCLAJES["M.O. Anclajes"]

    materiales = [
        {"nombre": "Sika AnchorFix 300ml", "unidad": "tubo", "cantidad": tubos, "vr_unitario": precio_sika},
        {"nombre": f"Varilla Roscada ø{diametro_mm}mm", "unidad": "und", "cantidad": cantidad, "vr_unitario": precio_varilla},
        {"nombre": "Tuercas y Arandelas", "unidad": "juego", "cantidad": cantidad, "vr_unitario": precio_tuercas},
        {"nombre": f"Broca ø{diametro_broca}mm", "unidad": "und", "cantidad": 1, "vr_unitario": precio_broca},
        {"nombre": "Kit de Limpieza", "unidad": "kit", "cantidad": 1, "vr_unitario": precio_limpieza},
        {"nombre": "M.O. Anclajes", "unidad": "punto", "cantidad": cantidad, "vr_unitario": precio_mo},
    ]

    for m in materiales:
        m["vr_total"] = round(m["cantidad"] * m["vr_unitario"], 2)

    total = round(sum(m["vr_total"] for m in materiales), 2)

    return {
        "volumen_total_cm3": round(vol_total, 2),
        "tubos_calculados": tubos,
        "materiales": materiales,
        "total": total,
    }
