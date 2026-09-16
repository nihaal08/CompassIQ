import sys
sys.path.insert(0, '.')
from werkzeug.security import check_password_hash, generate_password_hash
from db import query_db

agent = query_db("SELECT * FROM department_agents WHERE email = 'tech.agent@compassiq.com'", one=True)
stored = agent['password']
print("Stored hash:", stored)

candidates = ['Agent@123', 'Admin@123', 'User@123', 'password123', 'agent123', 'password', 'Tech@123', 'tech123', 'admin', 'Agent', 'agent']
for c in candidates:
    if check_password_hash(stored, c):
        print(f"MATCH FOUND! Password is: '{c}'")
        break
else:
    print("NO MATCH found in common passwords.")

new_hash = generate_password_hash('Agent@123', method='scrypt')
print("Testing new hash with Agent@123:", check_password_hash(new_hash, 'Agent@123'))
