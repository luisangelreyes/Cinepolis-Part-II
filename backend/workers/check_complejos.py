import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()

cur.execute("SELECT * FROM COMPLEJO LIMIT 5")
colnames = [desc[0] for desc in cur.description]
print(f"Columnas: {colnames}")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(row)
else:
    print("La tabla COMPLEJO está vacía!")

cur.close()
conn.close()
