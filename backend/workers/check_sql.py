with open('cartelera_vision_worker.sql', encoding='utf-8') as f:
    lines = f.readlines()

inserts_funcion = [l for l in lines if 'INSERT INTO FUNCION' in l]
print(f"Total INSERT INTO FUNCION: {len(inserts_funcion)}")

if inserts_funcion:
    print("Primer insert:", inserts_funcion[0][:100], "...")
