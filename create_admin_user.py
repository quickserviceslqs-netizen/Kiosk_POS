from modules.users import ensure_admin_user

# Create a default admin user if missing
admin = ensure_admin_user("admin", "admin123")
print(f"Admin user created: {admin['username']}")
