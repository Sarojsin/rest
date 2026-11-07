import psycopg2
import json

c = psycopg2.connect('dbname=restaurant user=postgres password=tara host=localhost')
cur = c.cursor()

# Get the registration with sagardhami84@gmail.com
cur.execute("select id, restaurant_name, owner_email, plan_code, status, invitation_token_hash, invitation_expires_at from self_service_registrations where owner_email='sagardhami84@gmail.com'")
for r in cur.fetchall():
    print('Registration ID:', r[0])
    print('Restaurant name:', r[1])
    print('Owner email:', r[2])
    print('Plan code:', r[3])
    print('Status:', r[4])
    print('Invitation token hash:', r[5])
    print('Invitation expires at:', r[6])
    
    # Check the restaurants table
    cur.execute('select id, name, slug from restaurants where id = %s', (r[0],))
    cur_res = cur.fetchone()
    if cur_res:
        print('Restaurant:', cur_res)
    
c.close()