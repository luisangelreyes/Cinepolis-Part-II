from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:1234@localhost:5432/secret_wars')
with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='asiento'")).fetchall()
    print([r[0] for r in res])
