PRECIOS_CIELO_RASO: dict[str, float] = {
    "Lamina de yeso 1.22x2.44": 35000.0,
    "Canal perimetral 3.05m": 10000.0,
    "Viga principal (canal) 3.05m": 11000.0,
    "Viga secundaria (montante) 3.05m": 12000.0,
    "Colgador / pendon": 1500.0,
    "Varilla roscada 3m": 8000.0,
    "Tornillo punta broca": 70.0,
    "Cinta de papel": 8000.0,
    "Masilla / pasta (bolsa 20kg)": 35000.0,
    "M.O. Cielo Raso": 25000.0,
}

VALORES_DEFAULT_CR = {
    "desperdicio": 0.05,
    "sep_vp": 1.2,
    "sep_vs": 0.5,
    "sep_colg": 1.2,
    "h_colg": 0.5,
    "l_varilla": 3.0,
    "factor_tornillos": 25,
    "kg_m2_masilla": 0.5,
    "n_manos_masilla": 2,
    "rendimiento_m2_dia": 12,
    "n_operarios": 2,
    "jornal": 120000,
}


def calcular_cielo_raso(
    an: float,
    la: float,
    desp: float = 0.05,
    sep_vp: float = 1.2,
    sep_vs: float = 0.5,
    sep_colg: float = 1.2,
    h_colg: float = 0.5,
    l_varilla: float = 3.0,
    factor_torn: int = 25,
    kg_m2_masilla: float = 0.5,
    n_manos_masilla: int = 2,
    rendimiento_m2_dia: float = 12,
    n_operarios: int = 2,
    jornal: float = 120000,
    con_varilla: bool = False,
    precios: dict[str, float] | None = None,
) -> dict:
    if an <= 0 or la <= 0:
        raise ValueError("Ancho y largo deben ser > 0")

    p = precios or PRECIOS_CIELO_RASO
    A = an * la
    P = 2 * (an + la)

    lamina = round(A / 2.9768 * (1 + desp), 2)
    canal_per = round(P / 3.05, 2)
    viga_ppal = round((an / sep_vp + 1) * la / 3.05, 2)
    viga_sec = round((la / sep_vs + 1) * an / 3.05, 2)
    colgadores = round(A / (sep_vp * sep_colg), 2)
    varillas = round(colgadores * h_colg / l_varilla, 2) if con_varilla else 0
    tornillos = round(A * factor_torn)
    juntas_v = an / 1.22
    juntas_h = la / 2.44
    cinta = round(juntas_v * la + juntas_h * an, 2)
    masilla = round(A * kg_m2_masilla * n_manos_masilla, 2)
    mo_horas = round(A / rendimiento_m2_dia * n_operarios * 8, 2)

    materiales = [
        {"nombre": "Lamina de yeso 1.22x2.44", "unidad": "und", "cantidad": lamina, "vr_unitario": p["Lamina de yeso 1.22x2.44"]},
        {"nombre": "Canal perimetral 3.05m", "unidad": "und", "cantidad": canal_per, "vr_unitario": p["Canal perimetral 3.05m"]},
        {"nombre": "Viga principal (canal) 3.05m", "unidad": "und", "cantidad": viga_ppal, "vr_unitario": p["Viga principal (canal) 3.05m"]},
        {"nombre": "Viga secundaria (montante) 3.05m", "unidad": "und", "cantidad": viga_sec, "vr_unitario": p["Viga secundaria (montante) 3.05m"]},
        {"nombre": "Colgador / pendon", "unidad": "und", "cantidad": colgadores, "vr_unitario": p["Colgador / pendon"]},
    ]
    if con_varilla:
        materiales.append({"nombre": "Varilla roscada 3m", "unidad": "und", "cantidad": varillas, "vr_unitario": p["Varilla roscada 3m"]})
    materiales += [
        {"nombre": "Tornillo punta broca", "unidad": "und", "cantidad": tornillos, "vr_unitario": p["Tornillo punta broca"]},
        {"nombre": "Cinta de papel", "unidad": "ml", "cantidad": cinta, "vr_unitario": p["Cinta de papel"]},
        {"nombre": "Masilla / pasta", "unidad": "kg", "cantidad": masilla, "vr_unitario": p["Masilla / pasta (bolsa 20kg)"]},
        {"nombre": "M.O. Cielo Raso", "unidad": "hr", "cantidad": mo_horas, "vr_unitario": p["M.O. Cielo Raso"]},
    ]

    for m in materiales:
        m["vr_total"] = round(m["cantidad"] * m["vr_unitario"], 2)

    total = round(sum(m["vr_total"] for m in materiales), 2)

    return {
        "an": an,
        "la": la,
        "area_m2": round(A, 2),
        "perimetro_ml": round(P, 2),
        "materiales": materiales,
        "total": total,
    }
