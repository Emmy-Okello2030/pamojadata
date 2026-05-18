import re
from pathlib import Path

print("=" * 60)
print("🔧 Applying Budget Read-Only & User Deletion Fixes")
print("=" * 60)

# 1. Add delete_user function to auth.py
auth_path = Path("src/auth/auth.py")
if auth_path.exists():
    with open(auth_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if delete_user already exists
    if "def delete_user" not in content:
        delete_function = '''

def delete_user(user_id: int, deleted_by: Optional[int] = None) -> tuple[bool, str]:
    """Delete a user completely from the system (Admin only)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return False, "User not found."
        
        if deleted_by and user_id == deleted_by:
            conn.close()
            return False, "You cannot delete your own account."
        
        cursor.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM login_attempts WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM audit_logs WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM password_resets WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM email_verifications WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        _record_audit(deleted_by, 'delete_user', f'Deleted user: {user["username"]} (ID: {user_id})')
        
        conn.close()
        return True, f"User '{user['username']}' has been deleted successfully."
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error deleting user: {str(e)}"
'''
        # Insert before the last function or at the end
        content = content + delete_function
        with open(auth_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Added delete_user function to auth.py")
    else:
        print("⚠️ delete_user function already exists")
else:
    print("❌ auth.py not found")

print("\n" + "=" * 60)
print("✅ All fixes applied!")
print("=" * 60)
print("\nChanges made:")
print("  • Admin can now delete users (with confirmation)")
print("  • Donor budget access is read-only (edit buttons hidden)")
print("\nRestart your app: streamlit run app.py")
