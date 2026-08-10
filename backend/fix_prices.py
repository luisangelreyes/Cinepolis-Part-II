from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:1234@localhost:5432/secret_wars')

def fix_missing_prices():
    with engine.begin() as conn:
        # Get all complexes that have 2D Tradicional sessions but NO Admisión General price
        query_missing = '''
            SELECT DISTINCT s.complejo_id 
            FROM FUNCION f JOIN SALA s ON f.sala_id = s.sala_id
            WHERE f.formato_id = 11 AND s.tipo_sala = 'Tradicional'
            AND NOT EXISTS (
                SELECT 1 FROM PRECIO_BOLETO pb 
                WHERE pb.complejo_id = s.complejo_id 
                  AND pb.formato_id = 11 
                  AND pb.tipo_sala = 'Tradicional' 
                  AND pb.tipo_boleto_id = 1
            )
        '''
        missing_complejos = [row.complejo_id for row in conn.execute(text(query_missing)).fetchall()]
        
        if not missing_complejos:
            print("No missing complexes.")
            return

        print(f"Missing complexes: {missing_complejos}")
        
        # Insert Admisión General (1), Niños (8), Tercera Edad (9) for each
        # We use a base generic price
        insert_query = text('''
            INSERT INTO PRECIO_BOLETO (complejo_id, formato_id, tipo_boleto_id, tipo_sala, precio, cargo_servicio_online)
            VALUES (:cid, 11, :tbid, 'Tradicional', :precio, 6.00)
            ON CONFLICT ON CONSTRAINT uq_precio_boleto DO NOTHING
        ''')
        
        for cid in missing_complejos:
            conn.execute(insert_query, {'cid': cid, 'tbid': 1, 'precio': 90.00})
            conn.execute(insert_query, {'cid': cid, 'tbid': 8, 'precio': 80.00})
            conn.execute(insert_query, {'cid': cid, 'tbid': 9, 'precio': 80.00})
            
        print(f"Inserted standard prices for {len(missing_complejos)} complexes.")

if __name__ == '__main__':
    fix_missing_prices()
