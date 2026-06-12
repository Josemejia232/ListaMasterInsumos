"""Script para clasificar productos Inscal existentes."""
import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import Producto
from app.routers.materiales import _clasificar_categoria

db = SessionLocal()
prods = db.query(Producto).filter(Producto.tienda.ilike("inscal")).all()
count = 0
for p in prods:
    cat = _clasificar_categoria(p.material)
    if cat and p.categoria != cat:
        p.categoria = cat
        count += 1
        print(f"ID={p.id} material={p.material} -> categoria={cat}")
db.commit()
db.close()
print(f"Clasificados: {count} de {len(prods)}")
