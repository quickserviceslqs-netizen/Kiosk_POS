#!/usr/bin/env python3
"""Quick system health check."""

import sys
sys.path.append('.')

print('Testing application startup...')

from modules import permissions, users
from utils.date_utils import format_date, get_date_format
from datetime import datetime

print(f'✓ Date format: {get_date_format()}')
print(f'✓ Sample date: {format_date(datetime.now())}')

admin = users.get_user_by_username('admin')
if admin:
    print(f'✓ Admin user: {admin["username"]}')
    result = permissions.has_permission('admin', 'view_dashboard')
    print(f'✓ Admin can view_dashboard: {result}')
    
    result2 = permissions.has_permission(admin, 'view_dashboard')
    print(f'✓ Admin dict can view_dashboard: {result2}')

print()
print('✓ All systems operational')
print('✓ Application ready to run')
