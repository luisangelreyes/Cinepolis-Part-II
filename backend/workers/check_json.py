import json

try:
    with open('cartelera_veracruz_completa.json', encoding='utf-8') as f:
        data = json.load(f)
        print(f"Peliculas guardadas: {len(data['peliculas'])}")
        print(f"Funciones guardadas: {len(data['funciones'])}")
except Exception as e:
    print(f"Error reading JSON: {e}")
