import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()

cur.execute("SELECT * FROM FORMATO_SALA")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(row)
else:
    print("La tabla FORMATO_SALA está vacía!")

cur.close()
conn.close()
