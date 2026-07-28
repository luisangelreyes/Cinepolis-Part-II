import psycopg2
conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print("TABLAS:", tables)
cur.close()
conn.close()
