import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()

cur.execute("SELECT DISTINCT tipo_asiento FROM asiento")
for row in cur.fetchall():
    print(f"Tipo: {row[0]}")

cur.close()
conn.close()
