from sqlalchemy import create_engine, text

engine = create_engine('postgresql://rest:rest@localhost:5433/restaurant')
with engine.connect() as c:
    for t in ['order_items', 'order_ratings']:
        cols = c.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{t}'")).fetchall()
        print(f'{t} columns:')
        for cname, ctype in cols:
            print(f'  {cname}: {ctype}')
        
        # Check FKs
        fks = c.execute(text(f"""
            SELECT kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu 
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu 
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = '{t}' AND tc.constraint_type = 'FOREIGN KEY'
        """)).fetchall()
        print(f'{t} FKs:')
        for fk in fks:
            print(f'  {fk}')
        print()