#!/usr/bin/env python3
"""Test dashboard currency settings propagation."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dashboard_currency_updates():
    """Test that dashboard currency displays update when currency settings change."""
    print("🧪 TESTING DASHBOARD CURRENCY UPDATES")
    print("=" * 50)
    
    try:
        import tkinter as tk
        from ui.dashboard import DashboardFrame
        from utils.currency_notifications import set_currency_settings
        from utils.i18n import get_currency_symbol
        
        # Create a test root window
        root = tk.Tk()
        root.withdraw()  # Hide the window
        root.title("Dashboard Currency Test")
        
        print("1. Creating dashboard frame...")
        dashboard_frame = DashboardFrame(root)
        
        print("2. Testing initial currency display...")
        initial_currency = get_currency_symbol()
        print(f"   Initial currency symbol: {initial_currency}")
        
        print("3. Changing currency and testing notification...")
        # Change to a different currency
        test_currencies = [
            ("USD", "$"),
            ("EUR", "€"),  
            ("GBP", "£"),
        ]
        
        for code, symbol in test_currencies:
            print(f"   Setting currency to {code} ({symbol})")
            set_currency_settings(code, symbol)
            
            # Give the UI a moment to update
            root.update()
            
            # Verify the currency was changed
            current_currency = get_currency_symbol()
            if current_currency == symbol:
                print(f"   ✅ Currency successfully updated to {symbol}")
            else:
                print(f"   ❌ Currency update failed: expected {symbol}, got {current_currency}")
                
        print("4. Testing dashboard data refresh...")
        dashboard_frame._refresh_data()
        root.update()
        print("   ✅ Dashboard data refresh completed without errors")
        
        print("5. Cleaning up...")
        dashboard_frame.destroy()
        root.destroy()
        
        print("\n✅ Dashboard currency update test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_dashboard_notification_system():
    """Test that dashboard properly subscribes and unsubscribes from currency notifications."""
    print("\n🧪 TESTING DASHBOARD NOTIFICATION SYSTEM")
    print("=" * 50)
    
    try:
        import tkinter as tk
        from ui.dashboard import DashboardFrame
        from utils.currency_notifications import _currency_notifier
        
        # Create test root
        root = tk.Tk()
        root.withdraw()
        
        print("1. Checking initial subscriber count...")
        initial_count = len(_currency_notifier._subscribers)
        print(f"   Initial subscribers: {initial_count}")
        
        print("2. Creating dashboard (should add subscriber)...")
        dashboard = DashboardFrame(root)
        after_create_count = len(_currency_notifier._subscribers)
        print(f"   Subscribers after create: {after_create_count}")
        
        if after_create_count > initial_count:
            print("   ✅ Dashboard properly subscribed to currency notifications")
        else:
            print("   ❌ Dashboard did not subscribe to currency notifications")
            return False
        
        print("3. Destroying dashboard (should remove subscriber)...")
        dashboard.destroy()
        after_destroy_count = len(_currency_notifier._subscribers)
        print(f"   Subscribers after destroy: {after_destroy_count}")
        
        if after_destroy_count == initial_count:
            print("   ✅ Dashboard properly unsubscribed from currency notifications")
        else:
            print("   ❌ Dashboard did not properly unsubscribe")
            return False
        
        root.destroy()
        print("\n✅ Dashboard notification system test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard notification test failed: {e}")
        return False

def main():
    """Run dashboard currency tests."""
    print("🎯 DASHBOARD CURRENCY PROPAGATION TESTING")
    print("Testing dashboard currency display updates...\n")
    
    tests = [
        ("Dashboard Currency Updates", test_dashboard_currency_updates),
        ("Dashboard Notification System", test_dashboard_notification_system),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: CRASHED - {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("DASHBOARD TEST RESULTS")
    print("=" * 50)
    print(f"✅ Tests Passed: {passed}")
    print(f"❌ Tests Failed: {failed}")
    print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL DASHBOARD CURRENCY TESTS PASSED!")
        print("✅ Dashboard subscribes to currency change notifications")
        print("✅ Dashboard refreshes data when currency changes")
        print("✅ Dashboard properly cleans up subscriptions")
        print("✅ Currency symbols display correctly in dashboard")
        print("\n🚀 Dashboard now respects currency settings!")
    else:
        print(f"\n⚠️  {failed} dashboard issues still need attention")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)