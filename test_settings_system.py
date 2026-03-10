"""
Comprehensive Settings System Test

This script validates all settings functionality to ensure proper integration.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.init_db import get_setting, set_setting, get_connection
from modules.settings import get_business_name, set_business_name
from utils.theme import get_current_theme_name, set_theme
from modules.notifications import get_email_config, save_email_config


def test_database_settings():
    """Test core database settings functionality."""
    print("Testing database settings...")
    
    # Test set/get cycle
    test_key = "test_setting_key"
    test_value = "test_value_123"
    
    set_setting(test_key, test_value)
    retrieved = get_setting(test_key)
    
    assert retrieved == test_value, f"Expected {test_value}, got {retrieved}"
    
    # Clean up test setting
    with get_connection() as conn:
        conn.execute("DELETE FROM settings WHERE key = ?", (test_key,))
        conn.commit()
    
    print("✅ Database settings working correctly")


def test_business_settings():
    """Test business settings module."""
    print("Testing business settings module...")
    
    # Store original value
    original_name = get_business_name()
    
    # Test setting new value
    test_name = "Test Business Name"
    set_business_name(test_name)
    
    retrieved_name = get_business_name()
    assert retrieved_name == test_name, f"Expected {test_name}, got {retrieved_name}"
    
    # Restore original value
    set_business_name(original_name)
    
    print("✅ Business settings module working correctly")


def test_theme_settings():
    """Test theme settings."""
    print("Testing theme settings...")
    
    current_theme = get_current_theme_name()
    print(f"   Current theme: {current_theme}")
    
    # Verify theme can be retrieved
    assert current_theme in ["default", "dark", "light", "blue", "green"], \
        f"Unexpected theme: {current_theme}"
    
    print("✅ Theme settings working correctly")


def test_email_settings():
    """Test email configuration."""
    print("Testing email settings...")
    
    config = get_email_config()
    
    # Verify config has expected structure
    expected_keys = ["enabled", "smtp_server", "smtp_port", "smtp_username", 
                     "smtp_password", "from_email", "to_emails"]
    
    for key in expected_keys:
        assert key in config, f"Missing key in email config: {key}"
    
    # Test save/load cycle
    original_enabled = config["enabled"]
    config["enabled"] = not original_enabled
    
    save_email_config(config)
    
    # Reload and verify
    reloaded_config = get_email_config()
    assert reloaded_config["enabled"] == (not original_enabled), \
        "Email config save/load failed"
    
    # Restore original setting
    config["enabled"] = original_enabled
    save_email_config(config)
    
    print("✅ Email settings working correctly")


def test_common_settings_keys():
    """Test that common settings have reasonable defaults."""
    print("Testing common settings defaults...")
    
    # Currency settings
    currency_code = get_setting('currency_code') or get_setting('currency')
    currency_symbol = get_setting('currency_symbol')
    
    print(f"   Currency: {currency_code} ({currency_symbol})")
    
    # Business settings
    business_name = get_setting('business_name')
    receipt_footer = get_setting('receipt_footer')
    
    print(f"   Business: {business_name}")
    print(f"   Receipt footer: {receipt_footer}")
    
    # VAT settings
    vat_enabled = get_setting('cart_vat_enabled')
    print(f"   VAT enabled: {vat_enabled}")
    
    # Theme
    theme_name = get_setting('theme')
    print(f"   Theme setting: {theme_name}")
    
    print("✅ Common settings accessible")


def test_settings_persistence():
    """Test that settings persist across connections."""
    print("Testing settings persistence...")
    
    test_key = "persistence_test"
    test_value = "persistent_value_456"
    
    # Set value
    set_setting(test_key, test_value)
    
    # Create new connection and verify
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (test_key,))
        row = cursor.fetchone()
        
        assert row is not None, "Setting not found in database"
        stored_value = row['value'] if isinstance(row, dict) else row[0]
        assert stored_value == test_value, f"Expected {test_value}, got {stored_value}"
    
    # Clean up
    with get_connection() as conn:
        conn.execute("DELETE FROM settings WHERE key = ?", (test_key,))
        conn.commit()
    
    print("✅ Settings persistence working correctly")


def main():
    """Run all settings tests."""
    print("🔧 Starting Comprehensive Settings System Tests\n")
    
    try:
        test_database_settings()
        test_business_settings()
        test_theme_settings()
        test_email_settings()
        test_common_settings_keys()
        test_settings_persistence()
        
        print("\n✅ ALL SETTINGS TESTS PASSED!")
        print("Settings system is properly wired and working correctly.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()