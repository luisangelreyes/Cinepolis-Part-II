from sqlalchemy import create_engine, text
e = create_engine('postgresql://postgres:1234@localhost:5432/secret_wars')
with e.connect() as conn:
    res = conn.execute(text('SELECT c.slug, count(dc.producto_id) FROM COMPLEJO c JOIN CATALOGO_COMPLEJO cc ON c.complejo_id=cc.complejo_id JOIN DETALLE_CATALOGO dc ON cc.catalogo_id=dc.catalogo_id GROUP BY c.slug')).fetchall()
    print(res)
