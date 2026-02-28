from database.init_db import get_connection

with get_connection() as conn:
    try:
        rows = conn.execute('SELECT item_id, SUM(quantity) as qty FROM stock_movements WHERE DATE(created_at) BETWEEN ? AND ? AND movement_type = "purchase" GROUP BY item_id', ('2026-02-01', '2026-02-07')).fetchall()
        print('Received query result:', type(rows), len(rows))
        result = {r[0]: r[1] for r in rows}
        print('Dict result:', type(result), len(result))
    except Exception as e:
        print('Error:', e)
        import traceback
        traceback.print_exc()