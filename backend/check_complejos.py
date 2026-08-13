from check_query import engine
from sqlalchemy import text
with engine.connect() as conn:
    res = conn.execute(text("SELECT complejo_id, slug FROM COMPLEJO")).fetchall()
    for row in res:
        print(row)
