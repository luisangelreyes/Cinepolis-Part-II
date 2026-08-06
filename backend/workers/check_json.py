import json

with open('cartelera_veracruz_completa.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
    print("Primer película en cartelera:")
    # It's usually d[0]['cartelera'][0] ... let's just search for the first poster_url
    for complejo in d:
        if 'cartelera' in complejo:
            for c in complejo['cartelera']:
                if 'cartelera' in c:
                    for p in c['cartelera']:
                        print(p.get('titulo'), p.get('poster_url'))
                        break
                break
        break
