from sqlalchemy import create_engine, text

engine = create_engine('postgresql://rest:rest@localhost:5433/restaurant')
with engine.connect() as c:
    tables = c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
    print('Tables:', [t[0] for t in tables])

    for t in ['orders', 'order_items', 'order_ratings', 'restaurant_tables']:
        try:
            cols = c.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}' AND column_name='restaurant_id'")).fetchall()
            print(f'{t}.restaurant_id: exists={len(cols) > 0}')
        except Exception as e:
            print(f'{t}: table not found ({e})')

    for t in ['order_items', 'order_ratings', 'restaurant_tables']:
        try:
            cols = c.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}' AND column_name='branch_id'")).fetchall()
            print(f'{t}.branch_id: exists={len(cols) > 0}')
        except Exception as e:
            print(f'{t}: table not found ({e})')