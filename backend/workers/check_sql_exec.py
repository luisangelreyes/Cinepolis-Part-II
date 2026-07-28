import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()

with open('cartelera_vision_worker.sql', encoding='utf-8') as f:
    lines = f.readlines()

inserts_funcion = [l for l in lines if 'INSERT INTO FUNCION' in l]

if inserts_funcion:
    stmt = inserts_funcion[0]
    print("Executing:")
    print(stmt)
    cur.execute(stmt)
    print(f"Rows affected: {cur.rowcount}")
    conn.rollback()

cur.close()
conn.close()
