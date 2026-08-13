import requests

r = requests.get('http://localhost:8000/api/dulceria/cinepolis-el-dorado-veracruz')
menu = r.json()

for cat in menu['menu']:
    for prod in cat['productos']:
        nombre = prod['nombre']
        if 'M&M' not in nombre:
            continue
        precio_base = prod['precio']
        print(f'PRODUCTO: {nombre} | precio_base: {precio_base}')
        for paso in prod['personalizacion']:
            for regla in paso['reglas']:
                for op in regla['opciones']:
                    print(f'  {op["nombre"]} | precio_extra: {op["precio_extra"]}')
        print()
