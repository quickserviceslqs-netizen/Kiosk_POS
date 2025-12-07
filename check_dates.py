import sqlite3
from datetime import datetime

conn = sqlite3.connect('database/pos.db')
cursor = conn.execute('SELECT date, COUNT(*) as sales FROM sales GROUP BY date')
print('Sales by date:')
for row in cursor:
    print(f'  {row[0]}: {row[1]} sales')

print(f'\nToday is: {datetime.now().strftime("%Y-%m-%d")}')
print(f'This week range: 2025-12-01 to 2025-12-07')
conn.close()
