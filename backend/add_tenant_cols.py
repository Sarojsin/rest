import psycopg

URL = "postgresql://rest:rest@localhost:5433/restaurant"

columns_to_add = [
    ("restaurant_tables", ["tenant_id UUID", "permission_version INT DEFAULT 1"]),
    ("orders", ["tenant_id UUID", "permission_version INT DEFAULT 1"]),
    ("bills", ["tenant_id UUID", "permission_version INT DEFAULT 1"]),
    ("payments", ["tenant_id UUID", "permission_version INT DEFAULT 1"]),
    ("dining_sessions", ["tenant_id UUID", "permission_version INT DEFAULT 1"]),
]

conn = psycopg.connect(URL)
for table, cols in columns_to_add:
    for col_def in cols:
        col, typ = col_def.split(" ", 1)
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ};")
            print(f"Added {col} to {table}")
        except Exception as e:
            print(f"skip {table}.{col} (already exists or error): {e}")

conn.close()
print("Done.")