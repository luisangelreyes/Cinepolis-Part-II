import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()

# Ver la definición del CHECK constraint en rol
cur.execute("""
    SELECT pg_get_constraintdef(oid) 
    FROM pg_constraint 
    WHERE conname = 'pelicula_persona_rol_check'
""")
row = cur.fetchone()
print("CHECK constraint de rol:")
print(" ", row[0] if row else "No encontrado")

cur.close()
conn.close()
