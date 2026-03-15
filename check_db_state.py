#!/usr/bin/env python3
"""Check database state after fresh installation."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.init_db import get_connection
from modules.users import list_users

print('🔍 Checking Database State:')
print('=' * 30)

# Check users
users = list_users()
if users:
    print(f'✅ Users found: {len(users)}')
    for user in users:
        username = user.get('username', 'Unknown')
        role = user.get('role', 'Unknown')
        active = user.get('active', False)
        print(f'   - {username} ({role}) - Active: {active}')
else:
    print('⏳ No users found (fresh installation)')

print()

# Check settings  
with get_connection() as conn:
    cursor = conn.execute('SELECT key, value FROM settings ORDER BY key')
    settings = cursor.fetchall()
    
if settings:
    print(f'✅ Settings found: {len(settings)}')
    for key, value in settings[:5]:  # Show first 5
        print(f'   - {key}: {value}')
    if len(settings) > 5:
        print(f'   ... and {len(settings) - 5} more')
else:
    print('⏳ No settings found (fresh installation)')

print()
print('🎯 Analysis:')
if users:
    print('   Setup wizard has completed (users exist)')
else:
    print('   Setup wizard should be active (no users yet)')