from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:1234@localhost:5432/secret_wars')

def update_prices():
    with engine.begin() as conn:
        # Delete "Evento Especial" from 2D Tradicional in all complexes where it was inserted
        # The user said "evento especial no deberia estar"
        res = conn.execute(text("DELETE FROM PRECIO_BOLETO WHERE tipo_boleto_id = 13 AND formato_id = 11 AND tipo_sala = 'Tradicional'"))
        print(f"Deleted {res.rowcount} Evento Especial tickets from 2D Tradicional.")

        # Update the generic prices we inserted earlier to match the original page
        # Base prices: 70.00 (General) and 55.00 (Niños/Tercera Edad) so with 6.00 fee they become 76.00 and 61.00
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 70.00 WHERE tipo_boleto_id = 1 AND precio = 90.00 AND formato_id = 11 AND tipo_sala = 'Tradicional'"))
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 55.00 WHERE tipo_boleto_id = 8 AND precio = 80.00 AND formato_id = 11 AND tipo_sala = 'Tradicional'"))
        conn.execute(text("UPDATE PRECIO_BOLETO SET precio = 55.00 WHERE tipo_boleto_id = 9 AND precio = 80.00 AND formato_id = 11 AND tipo_sala = 'Tradicional'"))
        print("Updated standard prices to match the original page (70.00 base, 55.00 base).")

if __name__ == '__main__':
    update_prices()
