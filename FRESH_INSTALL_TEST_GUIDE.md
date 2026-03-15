## Fresh Installation Test Guide 🧪

### Current State ✅
- **Database**: Fresh database created (`pos_f7ab1b7c.db`)
- **Users**: None (triggers setup wizard)
- **Settings**: Only default inventory costing method
- **Application**: Running and ready for setup

### What You Should See 👀

#### 1. Landing Screen or Setup Wizard
The application should display either:
- **Landing Screen**: Choose between "Set Up Live Store" or "Try Demo"
- **Setup Wizard**: Direct entry to configuration steps

#### 2. Setup Wizard Steps
If/when you enter the setup wizard, you should see:
1. **Welcome** - Introduction screen
2. **Database** - Database initialization (should be auto-completed)
3. **Admin** - Create administrator account
4. **Config** - Business name, currency, date format ⭐
5. **Preferences** - Theme, receipt footer
6. **Complete** - Finalization

### Key Testing Points 🎯

#### ⭐ **MAIN FIX TO TEST: Currency Selection**
- **Step 3 (Config)**: Currency dropdown should show **181 currencies**
- **Previously**: Only showed 9 currencies (USD, EUR, GBP, KES, ZAR, CAD, AUD, JPY, CNY)
- **Now**: Should include all major world currencies alphabetically sorted
- **Look for**: CHF, SEK, NOK, DKK, NGN, GHS, INR, BRL, MXN, etc.

#### Settings Persistence Test
After completing setup:
1. **Business name** appears in UI/receipts
2. **Selected currency** formats amounts correctly
3. **Theme** is applied immediately
4. **Date format** is used throughout system

### Test Scenarios 🧪

#### Scenario 1: Comprehensive Currency Test
1. Go to Config step
2. Open currency dropdown
3. Verify 181 currencies are available
4. Select a previously missing currency (e.g., CHF, INR, BRL)
5. Complete setup
6. Verify currency formatting works

#### Scenario 2: Settings Application Test
1. Configure business name: "Test Fresh Install"
2. Select currency: EUR (€)
3. Choose theme: Dark
4. Set date format: DD/MM/YYYY
5. Complete setup
6. Verify all settings are active

### Success Criteria ✅
- [ ] Currency dropdown shows 181+ currencies (not 9)
- [ ] Setup completes without errors
- [ ] Business name appears in application
- [ ] Currency formatting uses selected currency
- [ ] Selected theme is applied
- [ ] All settings persist after restart

### If Issues Occur ⚠️
Check the logs or database state using:
```bash
python check_db_state.py
```

The application is now ready for comprehensive testing of the setup wizard improvements!