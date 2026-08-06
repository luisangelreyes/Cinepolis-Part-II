import psycopg2

conn = psycopg2.connect('postgresql://postgres:1234@localhost:5432/secret_wars')
cur = conn.cursor()

# Get the CHECK constraint definition for SALA
cur.execute("""
    SELECT conname, pg_get_constraintdef(oid) 
    FROM pg_constraint 
    WHERE conrelid = 'sala'::regclass 
    AND contype = 'c'
""")
for row in cur.fetchall():
    print(f"Constraint: {row[0]}")
    print(f"Definition: {row[1]}")
    print()

# Also get distinct tipo_sala values currently in the table
cur.execute("SELECT DISTINCT tipo_sala FROM SALA ORDER BY tipo_sala")
print("Current tipo_sala values in SALA:")
for row in cur.fetchall():
    print(f"  - '{row[0]}'")

cur.close()
conn.close()
