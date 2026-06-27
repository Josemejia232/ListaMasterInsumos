PRECIOS_YESO: dict[str, float] = {
    "Lamina de yeso 1.22x2.44": 35000.0,
    "Montante 3.05m": 12000.0,
    "Canal 3.05m": 10000.0,
    "Tornillo punta broca": 80.0,
    "Cinta de papel": 8000.0,
    "Masilla / pasta (bolsa 20kg)": 35000.0,
    "Lana mineral (m²)": 18000.0,
    "M.O. Drywall": 25000.0,
}

VALORES_DEFAULT = {
    "desperdicio": 0.05,
    "factor_tornillos": 30,
    "kg_m2_masilla": 0.5,
    "n_manos_masilla": 2,
    "rendimiento_m2_dia": 12,
    "n_operarios": 2,
    "jornal": 120000,
}


def calcular_yeso(
    h: float,
    l: float,
    e: float,
    con_lana: bool = False,
    desp: float = 0.05,
    factor_torn: int = 30,
    kg_m2_masilla: float = 0.5,
    n_manos_masilla: int = 2,
    rendimiento_m2_dia: float = 12,
    n_operarios: int = 2,
    jornal: float = 120000,
    precios: dict[str, float] | None = None,
) -> dict:
    if h <= 0 or l <= 0 or e <= 0:
        raise ValueError("Altura, longitud y separacion deben ser > 0")
    if e > l:
        raise ValueError("Separacion de montantes no puede superar la longitud")

    p = PRECIOS_YESO.copy()
    if precios:
        for k, v in precios.items():
            if v is not None:
                p[k] = v
    A = h * l

    lamina = round(A * 2 / 2.9768 * (1 + desp), 2)
    montantes = round((l / e + 1) * h / 3.05, 2)
    canales = round(l * 2 / 3.05, 2)
    tornillos = round(A * 2 * factor_torn)
    juntas_v = l / 1.22
    juntas_h = h / 2.44
    cinta = round(juntas_v * h * 2 + juntas_h * l * 2, 2)
    masilla = round(A * 2 * kg_m2_masilla * n_manos_masilla, 2)
    lana = round(A * (1 + desp), 2) if con_lana else 0
    mo_horas = round(A / rendimiento_m2_dia * n_operarios * 8, 2)

    materiales = [
        {"nombre": "Lamina de yeso 1.22x2.44", "unidad": "und", "cantidad": lamina, "vr_unitario": p["Lamina de yeso 1.22x2.44"]},
        {"nombre": "Montante 3.05m", "unidad": "und", "cantidad": montantes, "vr_unitario": p["Montante 3.05m"]},
        {"nombre": "Canal 3.05m", "unidad": "und", "cantidad": canales, "vr_unitario": p["Canal 3.05m"]},
        {"nombre": "Tornillo punta broca", "unidad": "und", "cantidad": tornillos, "vr_unitario": p["Tornillo punta broca"]},
        {"nombre": "Cinta de papel", "unidad": "ml", "cantidad": cinta, "vr_unitario": p["Cinta de papel"]},
        {"nombre": "Masilla / pasta", "unidad": "kg", "cantidad": masilla, "vr_unitario": p["Masilla / pasta (bolsa 20kg)"]},
    ]
    if con_lana:
        materiales.append({"nombre": "Lana mineral", "unidad": "m²", "cantidad": lana, "vr_unitario": p["Lana mineral (m²)"]})
    materiales.append({"nombre": "M.O. Drywall", "unidad": "hr", "cantidad": mo_horas, "vr_unitario": p["M.O. Drywall"]})

    for m in materiales:
        m["vr_total"] = round(m["cantidad"] * m["vr_unitario"], 2)

    total = round(sum(m["vr_total"] for m in materiales), 2)

    return {
        "h": h,
        "l": l,
        "area_m2": round(A, 2),
        "e": e,
        "con_lana": con_lana,
        "materiales": materiales,
        "total": total,
    }
