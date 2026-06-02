from app.database import engine
from sqlalchemy import inspect, text

insp = inspect(engine)
for table in insp.get_table_names():
    print(f"\n=== {table} ===")
    for col in insp.get_columns(table):
        print(f"  {col['name']:20} {str(col['type']):20} nullable={col['nullable']}")

print("\n\n=== productos ===")
with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, codigo, descripcion, valor, categoria, origen FROM productos ORDER BY id")).fetchall()
    for r in rows:
        print(f"  id={r[0]} cod={r[1]} desc={r[2][:50]} valor={r[3]} cat={r[4]} origen={r[5]}")

print("\n=== usuarios ===")
with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, email, activo, tipo FROM usuarios ORDER BY id")).fetchall()
    for r in rows:
        print(f"  id={r[0]} email={r[1]} activo={r[2]} tipo={r[3]}")
