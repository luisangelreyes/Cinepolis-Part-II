import json
with open('cartelera_veracruz_completa.json', encoding='utf-8') as f:
    d = json.load(f)
    if d['funciones']:
        print("Muestra 1:", d['funciones'][0]['datetime'])
        print("Muestra 2:", d['funciones'][1]['datetime'])
    else:
        print("No hay funciones")
