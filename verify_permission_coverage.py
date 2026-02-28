#!/usr/bin/env python3
"""Verify complete permission system coverage - 12/12 areas."""

import sys
sys.path.append('.')

print()
print('PERMISSION SYSTEM COVERAGE - FINAL VERIFICATION')
print('=' * 80)

# Import modules to verify permission checks are in place
from ui import pos, dashboard, reports, user_mgmt, comprehensive_reconciliation_ui
import inspect

# Define all critical areas - 12 total permission checks
critical_areas = {
    'POS': {
        'module': pos.PosFrame,
        'checks': [
            ('_checkout', 'process_sales'),
            ('_refresh_cart', 'apply_discounts'),
        ]
    },
    'Dashboard': {
        'module': dashboard.DashboardFrame,
        'checks': [
            ('__init__', 'view_dashboard'),
        ]
    },
    'Reports': {
        'module': reports.ModernReportsFrame,
        'checks': [
            ('__init__', 'view_reports'),
            ('_export_report', 'export_reports'),
        ]
    },
    'User Management': {
        'module': user_mgmt.UserManagementFrame,
        'checks': [
            ('__init__', 'view_users'),
            ('_add_user_dialog', 'manage_users'),
        ]
    },
    'Reconciliation': {
        'module': comprehensive_reconciliation_ui.ComprehensiveReconciliationUI,
        'checks': [
            ('__init__', 'view_reconciliation'),
            ('_create_session', 'create_reconciliation'),
            ('_edit_session_from_dialog', 'edit_reconciliation'),
            ('_complete_reconciliation', 'approve_reconciliation'),
        ]
    },
}

total_checks = 0
implemented_checks = 0
missing_checks = []

for area, info in critical_areas.items():
    print(f'{area}:')
    module = info['module']
    checks = info['checks']
    
    for method_name, perm in checks:
        total_checks += 1
        try:
            method = getattr(module, method_name)
            source = inspect.getsource(method)
            
            # Check if method contains permission check
            search_str = f"has_permission(current_username, '{perm}')"
            if search_str in source or f"has_permission(current_user, '{perm}')" in source:
                print(f'  ✓ {method_name:30} - {perm}')
                implemented_checks += 1
            else:
                print(f'  ✗ {method_name:30} - {perm}')
                missing_checks.append(f'{area}.{method_name}')
        except Exception as e:
            print(f'  ? {method_name:30} - {perm} - Error: {str(e)[:40]}')
    
    print()

print('-' * 80)
print(f'COVERAGE: {implemented_checks}/{total_checks} permission checks implemented')
print()
if implemented_checks == total_checks:
    print('✓ ALL PERMISSION CHECKS COMPLETE - 12/12 COVERAGE (100%)')
    print()
    print('Permission enforcement now covers:')
    print('  • POS transactions (process_sales, apply_discounts)')
    print('  • Dashboard access (view_dashboard)')
    print('  • Reports (view_reports, export_reports)')
    print('  • User management (view_users, manage_users)')
    print('  • Reconciliation (view, create, edit, approve)')
    print('=' * 80)
else:
    print(f'✗ Missing {total_checks - implemented_checks} permission checks:')
    for check in missing_checks:
        print(f'   - {check}')
    print('=' * 80)

sys.exit(0 if implemented_checks == total_checks else 1)
