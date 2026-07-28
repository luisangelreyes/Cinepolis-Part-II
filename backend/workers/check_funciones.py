import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM FUNCION")
print(f"Funciones totales: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM FUNCION WHERE activa = TRUE")
print(f"Funciones activas: {cur.fetchone()[0]}")

cur.close()
conn.close()
