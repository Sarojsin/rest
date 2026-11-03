from sqlalchemy import create_engine, text

engine = create_engine('postgresql://rest:rest@localhost:5433/restaurant')
with engine.connect() as c:
    # Check restaurant_tables full schema
    cols = c.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='restaurant_tables'")).fetchall()
    print('restaurant_tables columns:')
    for cname, ctype in cols:
        print(f'  {cname}: {ctype}')
    
    # Check FKs on restaurant_tables
    fks = c.execute(text("""
        SELECT kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu 
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu 
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = 'restaurant_tables' AND tc.constraint_type = 'FOREIGN KEY'
    """)).fetchall()
    print(f'restaurant_tables FKs:')
    for fk in fks:
        print(f'  {fk}')