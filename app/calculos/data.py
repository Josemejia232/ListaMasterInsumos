from __future__ import annotations
from typing import Literal


class MaterialReceta:
    def __init__(self, nombre: str, unidad: str, cantidad: float, keywords: list[str] | None = None):
        self.nombre = nombre
        self.unidad = unidad
        self.cantidad = cantidad
        self.keywords = keywords or []


class Mezcla:
    def __init__(
        self,
        id: str,
        tipo: Literal["concreto", "mortero", "mamposteria"],
        nombre: str,
        proporcion: str,
        materiales: list[MaterialReceta],
        resistencia_psi: int | None = None,
        categoria: str | None = None,
    ):
        self.id = id
        self.tipo = tipo
        self.nombre = nombre
        self.proporcion = proporcion
        self.materiales = materiales
        self.resistencia_psi = resistencia_psi
        self.categoria = categoria


# ─── Precios fijos (agua, mano de obra — no están en la BD) ───
PRECIOS_FIJOS: dict[str, float] = {
    "Agua": 0.0,
    "M.O. CUADRILLA AG 1:2": 19888.0,
    "M.O. CUADRILLA AG 0:2": 11288.0,
    "Mezcladora a gasolina 1 1/2 bulto": 4125.0,
    "M.O. Mampostería": 15000.0,
}

# Palabras clave para buscar en BD por cada material
KEYWORDS_BD: dict[str, list[str]] = {
    "Cemento": ["cemento", "gris"],
    "Arena De peña": ["arena", "peña"],
    "Arena Lavada De Rio": ["arena", "rio", "lavada"],
    "Arena Lavada De Peña": ["arena", "peña", "lavada"],
    "Agregado grueso": ["gravilla", "agregado", "triturada", "canto", "rodado", "grava", "grueso"],
}


# ─── CONCRETOS ─────────────────────────────────────────────────

_CONCRETOS = [
    Mezcla(
        id="concreto-3500",
        tipo="concreto",
        nombre="Concreto 3.500 psi",
        proporcion="1:2:2",
        resistencia_psi=3500,
        materiales=[
            MaterialReceta("Cemento", "kl", 441.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena De peña", "m3", 0.74, keywords=["arena", "peña"]),
            MaterialReceta("Arena Lavada De Rio", "m3", 0.74, keywords=["arena", "rio", "lavada"]),
            MaterialReceta("Agregado grueso", "m3", 0.74, keywords=["gravilla", "agregado", "triturada"]),
            MaterialReceta("Agua", "lt", 230.0),
            MaterialReceta("M.O. CUADRILLA AG 1:2", "hc", 0.28),
            MaterialReceta("Mezcladora a gasolina 1 1/2 bulto", "hr", 0.52),
        ],
    ),
    Mezcla(
        id="concreto-3100",
        tipo="concreto",
        nombre="Concreto 3.100 psi",
        proporcion="1:2:3",
        resistencia_psi=3100,
        materiales=[
            MaterialReceta("Cemento", "kl", 367.5, keywords=["cemento", "gris"]),
            MaterialReceta("Arena De peña", "m3", 0.92, keywords=["arena", "peña"]),
            MaterialReceta("Arena Lavada De Rio", "m3", 0.61, keywords=["arena", "rio", "lavada"]),
            MaterialReceta("Agregado grueso", "m3", 0.92, keywords=["gravilla", "agregado", "triturada"]),
            MaterialReceta("Agua", "lt", 210.0),
            MaterialReceta("M.O. CUADRILLA AG 1:2", "hc", 0.28),
            MaterialReceta("Mezcladora a gasolina 1 1/2 bulto", "hr", 0.52),
        ],
    ),
    Mezcla(
        id="concreto-2900",
        tipo="concreto",
        nombre="Concreto 2.900 psi",
        proporcion="1:2:4",
        resistencia_psi=2900,
        materiales=[
            MaterialReceta("Cemento", "kl", 315.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena De peña", "m3", 0.48, keywords=["arena", "peña"]),
            MaterialReceta("Arena Lavada De Rio", "m3", 0.53, keywords=["arena", "rio", "lavada"]),
            MaterialReceta("Agregado grueso", "m3", 1.05, keywords=["gravilla", "agregado", "triturada"]),
            MaterialReceta("Agua", "lt", 305.0),
            MaterialReceta("M.O. CUADRILLA AG 1:2", "hc", 0.28),
            MaterialReceta("Mezcladora a gasolina 1 1/2 bulto", "hr", 0.52),
        ],
    ),
    Mezcla(
        id="concreto-2500",
        tipo="concreto",
        nombre="Concreto 2.500 psi",
        proporcion="1:3:3",
        resistencia_psi=2500,
        materiales=[
            MaterialReceta("Cemento", "kl", 315.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena De peña", "m3", 0.79, keywords=["arena", "peña"]),
            MaterialReceta("Arena Lavada De Rio", "m3", 0.79, keywords=["arena", "rio", "lavada"]),
            MaterialReceta("Agregado grueso", "m3", 0.79, keywords=["gravilla", "agregado", "triturada"]),
            MaterialReceta("Agua", "lt", 200.0),
            MaterialReceta("M.O. CUADRILLA AG 1:2", "hc", 0.28),
            MaterialReceta("Mezcladora a gasolina 1 1/2 bulto", "hr", 0.52),
        ],
    ),
    Mezcla(
        id="concreto-2300",
        tipo="concreto",
        nombre="Concreto 2.300 psi",
        proporcion="1:3:4",
        resistencia_psi=2300,
        materiales=[
            MaterialReceta("Cemento", "kl", 273.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena De peña", "m3", 0.69, keywords=["arena", "peña"]),
            MaterialReceta("Arena Lavada De Rio", "m3", 0.69, keywords=["arena", "rio", "lavada"]),
            MaterialReceta("Agregado grueso", "m3", 0.92, keywords=["gravilla", "agregado", "triturada"]),
            MaterialReceta("Agua", "lt", 198.0),
            MaterialReceta("M.O. CUADRILLA AG 1:2", "hc", 0.28),
            MaterialReceta("Mezcladora a gasolina 1 1/2 bulto", "hr", 0.52),
        ],
    ),
    Mezcla(
        id="concreto-1800",
        tipo="concreto",
        nombre="Concreto 1.800 psi",
        proporcion="1:3:5",
        resistencia_psi=1800,
        materiales=[
            MaterialReceta("Cemento", "kl", 230.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena De peña", "m3", 0.0, keywords=["arena", "peña"]),
            MaterialReceta("Arena Lavada De Rio", "m3", 0.56, keywords=["arena", "rio", "lavada"]),
            MaterialReceta("Agregado grueso", "m3", 0.92, keywords=["gravilla", "agregado", "triturada"]),
            MaterialReceta("Agua", "lt", 121.6),
            MaterialReceta("M.O. CUADRILLA AG 1:2", "hc", 0.28),
            MaterialReceta("Mezcladora a gasolina 1 1/2 bulto", "hr", 0.56),
        ],
    ),
]

# ─── MORTEROS ──────────────────────────────────────────────────

_MORTEROS = [
    Mezcla(
        id="mortero-1-10",
        tipo="mortero",
        nombre="Mortero 1:10",
        proporcion="1:10",
        materiales=[
            MaterialReceta("Cemento", "kl", 174.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena Lavada De Peña", "m3", 1.38, keywords=["arena", "peña", "lavada"]),
            MaterialReceta("Agua", "lt", 230.0),
            MaterialReceta("M.O. CUADRILLA AG 0:2", "hc", 2.26),
        ],
    ),
    Mezcla(
        id="mortero-1-2",
        tipo="mortero",
        nombre="Mortero 1:2",
        proporcion="1:2",
        materiales=[
            MaterialReceta("Cemento", "kl", 640.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena Lavada De Peña", "m3", 1.09, keywords=["arena", "peña", "lavada"]),
            MaterialReceta("Agua", "lt", 250.0),
            MaterialReceta("M.O. CUADRILLA AG 0:2", "hc", 2.26),
        ],
    ),
    Mezcla(
        id="mortero-1-3",
        tipo="mortero",
        nombre="Mortero 1:3",
        proporcion="1:3",
        materiales=[
            MaterialReceta("Cemento", "kl", 450.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena Lavada De Peña", "m3", 1.00, keywords=["arena", "peña", "lavada"]),
            MaterialReceta("Agua", "lt", 200.0),
            MaterialReceta("M.O. CUADRILLA AG 0:2", "hc", 2.26),
        ],
    ),
    Mezcla(
        id="mortero-1-4",
        tipo="mortero",
        nombre="Mortero 1:4",
        proporcion="1:4",
        materiales=[
            MaterialReceta("Cemento", "kl", 363.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena Lavada De Peña", "m3", 1.16, keywords=["arena", "peña", "lavada"]),
            MaterialReceta("Agua", "lt", 200.0),
            MaterialReceta("M.O. CUADRILLA AG 0:2", "hc", 2.26),
        ],
    ),
    Mezcla(
        id="mortero-1-5",
        tipo="mortero",
        nombre="Mortero 1:5",
        proporcion="1:5",
        materiales=[
            MaterialReceta("Cemento", "kl", 317.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena Lavada De Peña", "m3", 1.32, keywords=["arena", "peña", "lavada"]),
            MaterialReceta("Agua", "lt", 240.0),
            MaterialReceta("M.O. CUADRILLA AG 0:2", "hc", 2.26),
        ],
    ),
    Mezcla(
        id="mortero-1-6",
        tipo="mortero",
        nombre="Mortero 1:6",
        proporcion="1:6",
        materiales=[
            MaterialReceta("Cemento", "kl", 274.0, keywords=["cemento", "gris"]),
            MaterialReceta("Arena Lavada De Peña", "m3", 1.32, keywords=["arena", "peña", "lavada"]),
            MaterialReceta("Agua", "lt", 235.0),
            MaterialReceta("M.O. CUADRILLA AG 0:2", "hc", 2.26),
        ],
    ),
]

# ─── Diccionario unificado {id -> Mezcla} ──────────────────────

from app.calculos.data_mamposteria import _MAMPOSTERIA

MEZCLAS: dict[str, Mezcla] = {m.id: m for m in _CONCRETOS + _MORTEROS + _MAMPOSTERIA}
