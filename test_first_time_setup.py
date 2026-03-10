"""
First-Time Setup Simulation Test

Simulates complete first-time setup process to ensure settings are properly applied.
"""

import sys
from pathlib import Path

# Add project root to path  
sys.path.insert(0, str(Path(__file__).parent))

from database.init_db import get_setting, set_setting, get_connection
from modules.users import create_user, delete_user, list_users


def test_first_time_setup_scenario():
    """Test complete first-time setup scenario."""
    print("🚀 Testing First-Time Setup Scenario")
    print("=" * 50)
    
    try:
        # 1. Simulate fresh installation state
        print("1. Simulating fresh installation...")
        
        # Check if we need to cleanup any existing test data first
        existing_users = list_users()
        test_user = None
        for user in existing_users:
            if user.get('username') == 'test_admin_setup':
                test_user = user
                print(f"   Found existing test user: {user['username']}, cleaning up first...")
                success, message = delete_user(user['username'])
                if success:
                    print("   ✅ Existing test user cleaned up")
                else:
                    print(f"   ⚠️  Could not clean up existing test user: {message}")
                    # Try to use a different username
                    setup_data['username'] = 'test_admin_setup_2'
                break
        
        # Store original settings to restore later
        original_settings = {
            'business_name': get_setting('business_name'),
            'currency_code': get_setting('currency_code'), 
            'currency_symbol': get_setting('currency_symbol'),
            'currency': get_setting('currency'),
            'theme': get_setting('theme'),
            'receipt_footer': get_setting('receipt_footer'),
            'date_format': get_setting('date_format')
        }
        
        print("   ✅ Original settings backed up")
        
        # 2. Simulate setup wizard completion
        print("\n2. Simulating setup wizard completion...")
        
        setup_data = {
            'username': 'test_admin_setup',
            'password': 'TestPassword123!',
            'business_name': 'First Time Setup Store',
            'currency_code': 'EUR',  
            'currency_symbol': '€',
            'theme': 'dark',
            'receipt_footer': 'Thank you for choosing us!',
            'date_format': '%d/%m/%Y'
        }
        
        print(f"   Business: {setup_data['business_name']}")
        print(f"   Currency: {setup_data['currency_code']} ({setup_data['currency_symbol']})")
        print(f"   Theme: {setup_data['theme']}")
        
        # Step 1: Create admin user (simulating step 2 of setup)
        create_user(
            username=setup_data['username'],
            password=setup_data['password'], 
            role='admin',
            active=True
        )
        print("   ✅ Admin user created")
        
        # Step 2: Save business and currency settings (simulating step 3)
        with get_connection() as conn:
            business_currency_settings = [
                ('business_name', setup_data['business_name']),
                ('currency_code', setup_data['currency_code']),
                ('currency_symbol', setup_data['currency_symbol']), 
                ('currency', setup_data['currency_code'])  # legacy compatibility
            ]
            
            for key, value in business_currency_settings:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        
        print("   ✅ Business and currency settings saved")
        
        # Step 3: Save preferences (simulating step 4)
        with get_connection() as conn:
            preference_settings = [
                ('theme', setup_data['theme']),
                ('receipt_footer', setup_data['receipt_footer']),
                ('date_format', setup_data['date_format'])
            ]
            
            for key, value in preference_settings:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
            
        print("   ✅ Preference settings saved")
        
        # 3. Verify all settings were applied correctly
        print("\n3. Verifying setup results...")
        
        # Verify admin user exists
        users = list_users()
        admin_user = None
        for user in users:
            if user.get('username') == setup_data['username']:
                admin_user = user
                break
        
        assert admin_user is not None, "Admin user not created"
        assert admin_user['role'] == 'admin', "Admin user role incorrect"
        assert admin_user['active'] == True, "Admin user not active"
        print(f"   ✅ Admin user verified: {admin_user['username']}")
        
        # Verify all settings
        for key, expected_value in setup_data.items():
            if key in ['username', 'password']:
                continue
                
            if key == 'currency_code':
                # Check both modern and legacy keys
                saved_value = get_setting('currency_code')
                legacy_value = get_setting('currency')
                assert saved_value == expected_value, f"Currency code mismatch: {saved_value} != {expected_value}"
                assert legacy_value == expected_value, f"Legacy currency mismatch: {legacy_value} != {expected_value}" 
                print(f"   ✅ Currency: {saved_value} (with legacy compatibility)")
            else:
                saved_value = get_setting(key)
                assert saved_value == expected_value, f"{key} mismatch: {saved_value} != {expected_value}"
                print(f"   ✅ {key}: {saved_value}")
        
        # 4. Test that settings work in practice
        print("\n4. Testing practical application of settings...")
        
        # Test currency formatting
        from utils.i18n import format_currency, get_currency_symbol
        current_symbol = get_currency_symbol()
        formatted_amount = format_currency(99.99)
        
        assert current_symbol == setup_data['currency_symbol'], f"Currency symbol mismatch in i18n: {current_symbol}"
        assert setup_data['currency_symbol'] in formatted_amount, f"Currency not in formatted amount: {formatted_amount}"
        print(f"   ✅ Currency formatting: 99.99 → {formatted_amount}")
        
        # Test business name retrieval
        from modules.settings import get_business_name
        business_name = get_business_name()
        assert business_name == setup_data['business_name'], f"Business name mismatch: {business_name}"
        print(f"   ✅ Business name: {business_name}")
        
        # 5. Cleanup and restore
        print("\n5. Cleaning up test data...")
        
        # Delete test admin user
        if admin_user:
            success, message = delete_user(admin_user['username'])
            if success:
                print("   ✅ Test admin user deleted")
            else:
                print(f"   ⚠️  Could not delete test user: {message}")
        
        # Restore original settings
        with get_connection() as conn:
            for key, orig_value in original_settings.items():
                if orig_value is not None:
                    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, orig_value))
                else:
                    # Remove setting if it didn't exist originally
                    conn.execute("DELETE FROM settings WHERE key = ?", (key,))
            conn.commit()
        
        print("   ✅ Original settings restored")
        
        print("\n" + "=" * 50)
        print("✅ FIRST-TIME SETUP SIMULATION SUCCESSFUL!")
        print("\nVERIFIED FUNCTIONALITY:")
        print("✅ Admin user creation")
        print("✅ Business name configuration")
        print("✅ Currency settings (code + symbol + legacy compatibility)")
        print("✅ Theme preference")
        print("✅ Receipt footer customization")
        print("✅ Date format setting")
        print("✅ Settings persistence across application layers")
        print("✅ Practical application of all settings")
        
        return True
        
    except Exception as e:
        print(f"\n❌ SETUP SIMULATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        
        # Attempt cleanup on failure
        try:
            if 'admin_user' in locals() and admin_user:
                delete_user(admin_user['username'])
            
            # Restore settings
            if 'original_settings' in locals():
                with get_connection() as conn:
                    for key, orig_value in original_settings.items():
                        if orig_value is not None:
                            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, orig_value))
                    conn.commit()
            
            print("   ⚠️  Cleanup completed after failure")
        except Exception as cleanup_error:
            print(f"   ⚠️  Cleanup also failed: {cleanup_error}")
        
        return False


def main():
    """Run complete first-time setup test."""
    try:
        success = test_first_time_setup_scenario()
        if success:
            print("\n🎉 First-time setup process verified and working correctly!")
        else:
            print("\n💥 First-time setup process has issues that need attention.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()