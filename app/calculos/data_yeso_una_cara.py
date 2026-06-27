PRECIOS_YESO_UC: dict[str, float] = {
    "Lamina de yeso 1.22x2.44": 35000.0,
    "Montante 3.05m": 12000.0,
    "Canal 3.05m": 10000.0,
    "Tornillo punta broca": 80.0,
    "Cinta de papel": 8000.0,
    "Masilla / pasta (bolsa 20kg)": 35000.0,
    "M.O. Drywall": 25000.0,
}

VALORES_DEFAULT_UC: dict[str, float] = {
    "desperdicio": 0.05,
    "factor_tornillos": 15,
    "kg_m2_masilla": 0.5,
    "n_manos_masilla": 2,
    "rendimiento_m2_dia": 12,
    "n_operarios": 2,
    "jornal": 120000,
}


def calcular_yeso_una_cara(
    h: float,
    l: float,
    e: float,
    desp: float = 0.05,
    factor_torn: int = 15,
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

    p = PRECIOS_YESO_UC.copy()
    if precios:
        for k, v in precios.items():
            if v is not None:
                p[k] = v
    A = h * l

    lamina = round(A / 2.9768 * (1 + desp), 2)
    montantes = round((l / e + 1) * h / 3.05, 2)
    canales = round(l * 2 / 3.05, 2)
    tornillos = round(A * factor_torn)
    juntas_v = l / 1.22
    juntas_h = h / 2.44
    cinta = round(juntas_v * h + juntas_h * l, 2)
    masilla = round(A * kg_m2_masilla * n_manos_masilla, 2)
    mo_cant = round(A / rendimiento_m2_dia * n_operarios, 2)
    mo_total = round(mo_cant * jornal, 2)

    materiales = [
        {"nombre": "Lamina de yeso 1.22x2.44", "unidad": "und", "cantidad": lamina, "vr_unitario": p["Lamina de yeso 1.22x2.44"]},
        {"nombre": "Montante 3.05m", "unidad": "und", "cantidad": montantes, "vr_unitario": p["Montante 3.05m"]},
        {"nombre": "Canal 3.05m", "unidad": "und", "cantidad": canales, "vr_unitario": p["Canal 3.05m"]},
        {"nombre": "Tornillo punta broca", "unidad": "und", "cantidad": tornillos, "vr_unitario": p["Tornillo punta broca"]},
        {"nombre": "Cinta de papel", "unidad": "ml", "cantidad": cinta, "vr_unitario": p["Cinta de papel"]},
        {"nombre": "Masilla / pasta", "unidad": "kg", "cantidad": masilla, "vr_unitario": p["Masilla / pasta (bolsa 20kg)"]},
        {"nombre": "M.O. Drywall", "unidad": "jornal", "cantidad": mo_cant, "vr_unitario": jornal, "vr_total": mo_total},
    ]

    for m in materiales:
        if "vr_total" not in m:
            m["vr_total"] = round(m["cantidad"] * m["vr_unitario"], 2)

    total = round(sum(m["vr_total"] for m in materiales), 2)

    return {
        "h": h,
        "l": l,
        "area_m2": round(A, 2),
        "e": e,
        "materiales": materiales,
        "total": total,
    }
