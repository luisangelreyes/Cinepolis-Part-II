from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:1234@localhost:5432/secret_wars')

def update_xalapa_prices():
    with engine.begin() as conn:
        # Xalapa 3D prices based on screenshot
        # Admisión General 3D (tipo_boleto_id = 10)
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 113.00 WHERE complejo_id = 11 AND formato_id = 12 AND tipo_boleto_id = 10"))
        # Niños Digital 3D (tipo_boleto_id = 11)
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 92.00 WHERE complejo_id = 11 AND formato_id = 12 AND tipo_boleto_id = 11"))
        # Tercera Edad 3D (tipo_boleto_id = 12)
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 92.00 WHERE complejo_id = 11 AND formato_id = 12 AND tipo_boleto_id = 12"))
        
        # We should also update the 2D prices to be realistic compared to 3D. 3D is usually 20 MXN more expensive.
        # Admisión General 2D (tipo_boleto_id = 1) -> ~93.00
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 93.00 WHERE complejo_id = 11 AND formato_id = 11 AND tipo_boleto_id = 1"))
        # Niños 2D (tipo_boleto_id = 8) -> ~72.00
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 72.00 WHERE complejo_id = 11 AND formato_id = 11 AND tipo_boleto_id = 8"))
        # Tercera Edad 2D (tipo_boleto_id = 9) -> ~72.00
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 72.00 WHERE complejo_id = 11 AND formato_id = 11 AND tipo_boleto_id = 9"))

        print("Updated Xalapa prices to match the official screenshot.")

if __name__ == '__main__':
    update_xalapa_prices()
