import psycopg2
c = psycopg2.connect(host='localhost', dbname='restaurant', user='postgres', password='tara')
cur = c.cursor()

# Step 1: Drop the constraint
cur.execute('ALTER TABLE public.restaurant_tables DROP CONSTRAINT uq_tables_table_code')
print('Dropped constraint uq_tables_table_code')

# Step 2: Create composite unique index per branch
cur.execute('''
    CREATE UNIQUE INDEX uq_tables_table_code_per_branch
    ON public.restaurant_tables (table_code, branch_id)
''')
print('Created composite unique index uq_tables_table_code_per_branch ON (table_code, branch_id)')

c.commit()
c.close()
print('Constraint fix applied successfully!')