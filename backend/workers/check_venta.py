import psycopg2
conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()
cur.execute("SELECT column_name, character_maximum_length FROM information_schema.columns WHERE table_name = 'venta';")
for row in cur.fetchall():
    print(row)
