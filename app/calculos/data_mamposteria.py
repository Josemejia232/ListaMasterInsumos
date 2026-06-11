from app.calculos.data import Mezcla, MaterialReceta


_MAMPOSTERIA = [
    # === EXISTING ITEMS ===
    Mezcla(
        id="mamposteria-bloque-4",
        tipo="mamposteria",
        nombre="Muro en Bloque #4 (10x20x40 cm)",
        proporcion="1 m²",
        categoria="Divisorios",
        materiales=[
            MaterialReceta("Bloque #4 (10x20x40)", "und", 12.5, keywords=['bloque', '4', '10x20x40']),
            MaterialReceta("Mortero de pega", "m3", 0.02, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamposteria-bloque-5",
        tipo="mamposteria",
        nombre="Muro en Bloque #5 (10x20x40 cm)",
        proporcion="1 m²",
        categoria="Divisorios",
        materiales=[
            MaterialReceta("Bloque #5 (10x20x40)", "und", 12.5, keywords=['bloque', '5', '10x20x40']),
            MaterialReceta("Mortero de pega", "m3", 0.025, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamposteria-ladrillo-tolete",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Tolete (5x10x20 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo tolete (5x10x20)", "und", 50, keywords=['ladrillo', 'tolete']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamposteria-ladrillo-farol",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Farol (10x20x30 cm)",
        proporcion="1 m²",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Ladrillo farol (10x20x30)", "und", 16.5, keywords=['ladrillo', 'farol']),
            MaterialReceta("Mortero de pega", "m3", 0.025, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamposteria-ladrillo-tablete",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Tablete (4x10x20 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo tablete (4x10x20)", "und", 55, keywords=['ladrillo', 'tablete']),
            MaterialReceta("Mortero de pega", "m3", 0.02, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),


    # === LADRILLERA SANTAFÉ ===

    Mezcla(
        id="mamp-santafe-adoqu-n-cuarto-26-cobrizo",
        tipo="mamposteria",
        nombre="Piso en Adoquín Cuarto 26 Cobrizo (26x6x6 cm)",
        proporcion="1 m²",
        categoria="Adoquines",
        materiales=[
            MaterialReceta("Adoquín Cuarto 26 Cobrizo", "und", 64.0, keywords=['adoquín', 'cuarto', 'cobrizo']),
            MaterialReceta("Arena de Base", "m3", 0.07, keywords=['arena', 'base', 'rio']),
            MaterialReceta("Arena de Sello", "m3", 0.005, keywords=['arena', 'sello', 'fino']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-adoqu-n-cuarto-26-terracota",
        tipo="mamposteria",
        nombre="Piso en Adoquín Cuarto 26 Terracota (26x6x6 cm)",
        proporcion="1 m²",
        categoria="Adoquines",
        materiales=[
            MaterialReceta("Adoquín Cuarto 26 Terracota", "und", 64.0, keywords=['adoquín', 'cuarto', 'terracota']),
            MaterialReceta("Arena de Base", "m3", 0.07, keywords=['arena', 'base', 'rio']),
            MaterialReceta("Arena de Sello", "m3", 0.005, keywords=['arena', 'sello', 'fino']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-adoqu-n-español-tr-fico-pesado",
        tipo="mamposteria",
        nombre="Piso en Adoquín Español Tráfico Pesado (20x10x8 cm)",
        proporcion="1 m²",
        categoria="Adoquines",
        materiales=[
            MaterialReceta("Adoquín Español Tráfico Pesado", "und", 50.0, keywords=['adoquín', 'español', 'tráfico', 'pesado']),
            MaterialReceta("Arena de Base", "m3", 0.07, keywords=['arena', 'base', 'rio']),
            MaterialReceta("Arena de Sello", "m3", 0.005, keywords=['arena', 'sello', 'fino']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-adoqu-n-español-cobrizo",
        tipo="mamposteria",
        nombre="Piso en Adoquín Español Cobrizo (20x10x6 cm)",
        proporcion="1 m²",
        categoria="Adoquines",
        materiales=[
            MaterialReceta("Adoquín Español Cobrizo", "und", 50.0, keywords=['adoquín', 'español', 'cobrizo']),
            MaterialReceta("Arena de Base", "m3", 0.07, keywords=['arena', 'base', 'rio']),
            MaterialReceta("Arena de Sello", "m3", 0.005, keywords=['arena', 'sello', 'fino']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-adoqu-n-español-terracota",
        tipo="mamposteria",
        nombre="Piso en Adoquín Español Terracota (20x10x6 cm)",
        proporcion="1 m²",
        categoria="Adoquines",
        materiales=[
            MaterialReceta("Adoquín Español Terracota", "und", 50.0, keywords=['adoquín', 'español', 'terracota']),
            MaterialReceta("Arena de Base", "m3", 0.07, keywords=['arena', 'base', 'rio']),
            MaterialReceta("Arena de Sello", "m3", 0.005, keywords=['arena', 'sello', 'fino']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-portante-30-x-12-capuchino-h",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Portante 30 x 12 Capuchino H (29x12x9 cm)",
        proporcion="1 m²",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Ladrillo Portante 30 x 12 Capuchino H", "und", 33.3, keywords=['ladrillo', 'portante', 'capuchino']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-estructural-de-perforaci-n-vertical-doble-pared-medio-fachada-rojo",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Estructural de Perforación Vertical Doble Pared Medio Fachada Rojo (33x11.5x11 cm)",
        proporcion="1 m²",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Ladrillo Estructural de Perforación Vertical Doble Pared Medio Fachada Rojo", "und", 24.5, keywords=['ladrillo', 'estructural', 'perforación', 'vertical', 'doble', 'pared', 'medio', 'fachada', 'rojo']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-estructural-de-perforaci-n-vertical-doble-pared-pieza-entera",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Estructural de Perforación Vertical Doble Pared Pieza Entera (33x11.5x23 cm)",
        proporcion="1 m²",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Ladrillo Estructural de Perforación Vertical Doble Pared Pieza Entera", "und", 12.25, keywords=['ladrillo', 'estructural', 'perforación', 'vertical', 'doble', 'pared', 'pieza', 'entera']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-estructural-de-perforaci-n-vertical-medio-fachada-rojo-re",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Estructural de Perforación Vertical Medio fachada Rojo RE (33x11.5x11 cm)",
        proporcion="1 m²",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Ladrillo Estructural de Perforación Vertical Medio fachada Rojo RE", "und", 24.5, keywords=['ladrillo', 'estructural', 'perforación', 'vertical', 'medio', 'fachada', 'rojo']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-portante-30-terracota",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Portante 30 Terracota (29x14.5x9 cm)",
        proporcion="1 m²",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Ladrillo Portante 30 Terracota", "und", 33.3, keywords=['ladrillo', 'portante', 'terracota']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-portante-30-x-12-cocoa",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Portante 30 x 12 Cocoa (29x12x9 cm)",
        proporcion="1 m²",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Ladrillo Portante 30 x 12 Cocoa", "und", 33.3, keywords=['ladrillo', 'portante', 'cocoa']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-portante-30-x-12-terracota",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Portante 30 x 12 Terracota (29x12x9 cm)",
        proporcion="1 m²",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Ladrillo Portante 30 x 12 Terracota", "und", 33.3, keywords=['ladrillo', 'portante', 'terracota']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-pieza-media-de-traba",
        tipo="mamposteria",
        nombre="Muro en Pieza Media de Traba (33x11.5x11 cm) (por ml)",
        proporcion="1 ml",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Pieza Media de Traba", "ml", 2.08, keywords=['pieza', 'media', 'traba']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-pieza-media-de-traba-1",
        tipo="mamposteria",
        nombre="Muro en Pieza Media de Traba (16x11.5x23 cm) (por ml)",
        proporcion="1 ml",
        categoria="Estructurales",
        materiales=[
            MaterialReceta("Pieza Media de Traba", "ml", 2.08, keywords=['pieza', 'media', 'traba']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-gran-formato-liso-duna",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Gran Formato Liso Duna (39x11.5x5 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Gran Formato Liso Duna", "und", 41.7, keywords=['ladrillo', 'gran', 'formato', 'liso', 'duna']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-gran-formato-cobrizo",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Gran Formato Cobrizo (39x11.5x5 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Gran Formato Cobrizo", "und", 41.7, keywords=['ladrillo', 'gran', 'formato', 'cobrizo']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-gran-formato-cocoa",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Gran Formato Cocoa (39x11.5x5 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Gran Formato Cocoa", "und", 41.7, keywords=['ladrillo', 'gran', 'formato', 'cocoa']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-gran-formato-duna",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Gran Formato Duna (39x11.5x2.9 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Gran Formato Duna", "und", 41.7, keywords=['ladrillo', 'gran', 'formato', 'duna']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-gran-formato-terracota",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Gran Formato Terracota (39x11.5x5 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Gran Formato Terracota", "und", 41.7, keywords=['ladrillo', 'gran', 'formato', 'terracota']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-gran-formato-tierra",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Gran Formato Tierra (39x11.5x5 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Gran Formato Tierra", "und", 41.7, keywords=['ladrillo', 'gran', 'formato', 'tierra']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-prensado-liviano-6-titanio-h",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Prensado Liviano 6 Titanio H (24.5x12x6 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Prensado Liviano 6 Titanio H", "und", 56.0, keywords=['ladrillo', 'prensado', 'liviano', 'titanio']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-prensado-liviano-6-cm-capuchino-h",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Prensado Liviano 6 cm Capuchino H (24.5x12x6 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Prensado Liviano 6 cm Capuchino H", "und", 56.0, keywords=['ladrillo', 'prensado', 'liviano', 'capuchino']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-prensado-liviano-6-cm-cocoa-h",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Prensado Liviano 6 cm Cocoa H (24.5x12x6 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Prensado Liviano 6 cm Cocoa H", "und", 56.0, keywords=['ladrillo', 'prensado', 'liviano', 'cocoa']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-prensado-liviano-6-cm-coral-h",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Prensado Liviano 6 cm Coral H (24.5x12x6 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Prensado Liviano 6 cm Coral H", "und", 56.0, keywords=['ladrillo', 'prensado', 'liviano', 'coral']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-prensado-liviano-6-cm-terracota",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Prensado Liviano 6 cm Terracota (24.5x12x6 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Prensado Liviano 6 cm Terracota", "und", 3.6, keywords=['ladrillo', 'prensado', 'liviano', 'terracota']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-prensado-macizo-terracota",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Prensado Macizo Terracota (24.5x12x5.5 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Prensado Macizo Terracota", "und", 60.0, keywords=['ladrillo', 'prensado', 'macizo', 'terracota']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-ladrillo-tolete-fino-liviano-tierra",
        tipo="mamposteria",
        nombre="Muro en Ladrillo Tolete Fino Liviano Tierra (24.5x12x6 cm)",
        proporcion="1 m²",
        categoria="Fachadas",
        materiales=[
            MaterialReceta("Ladrillo Tolete Fino Liviano Tierra", "und", 56.0, keywords=['ladrillo', 'tolete', 'fino', 'liviano', 'tierra']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-bloque-n--4",
        tipo="mamposteria",
        nombre="Muro en Bloque N° 4 (33x9x23 cm)",
        proporcion="1 m²",
        categoria="Divisorios",
        materiales=[
            MaterialReceta("Bloque N° 4", "und", 12.25, keywords=['bloque']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-bloque-n--4-perforaci-n-vertical",
        tipo="mamposteria",
        nombre="Muro en Bloque N° 4 Perforación Vertical (33x9x23 cm)",
        proporcion="1 m²",
        categoria="Divisorios",
        materiales=[
            MaterialReceta("Bloque N° 4 Perforación Vertical", "und", 12.25, keywords=['bloque', 'perforación', 'vertical']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-bloque-n--5-perforaci-n-vertical",
        tipo="mamposteria",
        nombre="Muro en Bloque N° 5 Perforación Vertical (33x11.5x23 cm)",
        proporcion="1 m²",
        categoria="Divisorios",
        materiales=[
            MaterialReceta("Bloque N° 5 Perforación Vertical", "und", 12.25, keywords=['bloque', 'perforación', 'vertical']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-bloque-n--5",
        tipo="mamposteria",
        nombre="Muro en Bloque N° 5 (33x11.5x23 cm)",
        proporcion="1 m²",
        categoria="Divisorios",
        materiales=[
            MaterialReceta("Bloque N° 5", "und", 12.25, keywords=['bloque']),
            MaterialReceta("Mortero de pega", "m3", 0.03, keywords=['mortero', 'pega']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

    Mezcla(
        id="mamp-santafe-bloquel-n",
        tipo="mamposteria",
        nombre="Muro en Bloquelón",
        proporcion="1 m²",
        categoria="Placafacil",
        materiales=[
            MaterialReceta("Adhesivo cementicio", "sacos", 0.2, keywords=['adhesivo', 'cementicio', 'pegante']),
            MaterialReceta("M.O. Mampostería", "m2", 1.0),
        ],
    ),

]
