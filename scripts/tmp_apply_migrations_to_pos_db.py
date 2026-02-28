import json, shutil
cfg='config.json'
with open(cfg,'r') as f:
    old=json.load(f)
shutil.copy(cfg,cfg+'.bak')
old_db=old.get('db_path')
print('old db', old_db)
old['db_path']='C:\\Users\\ADMIN\\Kiosk_POS\\database\\pos.db'
with open(cfg,'w') as f:
    json.dump(old,f)

from database.migrations import run_pending_migrations
print('apply', run_pending_migrations())

# restore
with open(cfg,'w') as f:
    json.dump({'db_path': old_db}, f)
print('restored config to', old_db)