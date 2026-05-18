import os
import re
import sqlite3
import hashlib
import secrets
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

from src.database.db import DB_PATH as DEFAULT_DB_PATH

DB_PATH = os.environ.get("PAMOJADATA_DB_PATH", DEFAULT_DB_PATH)
PASSWORD_HASH_ALGORITHM = 'pbkdf2_sha256'
PASSWORD_HASH_ITERATIONS = int(os.environ.get('PAMOJADATA_HASH_ITERATIONS', '320000'))
PASSWORD_SALT_BYTES = int(os.environ.get('PAMOJADATA_SALT_BYTES', '32'))
SESSION_TOKEN_BYTES = 32
REFRESH_TOKEN_BYTES = 32
SESSION_EXPIRE_HOURS = int(os.environ.get('PAMOJADATA_SESSION_EXPIRE_HOURS', '8'))
REFRESH_EXPIRE_DAYS = int(os.environ.get('PAMOJADATA_REFRESH_EXPIRE_DAYS', '7'))

PUBLIC_SIGNUP_ROLES = ['Standard User']
PRIVILEGED_SIGNUP_ROLES = ['Admin', 'Staff/Manager', 'Moderator', 'Programme Manager', 'M&E Officer', 'Donor']

ROLES = [
    ('Admin', 'Full access to all modules'),
    ('Staff/Manager', 'Operational access'),
    ('Moderator', 'Quality and moderation access'),
    ('Programme Manager', 'Programme-level access'),
    ('M&E Officer', 'Data collection and quality'),
    ('Standard User', 'Standard access'),
    ('Donor', 'Read-only access'),
]

PERMISSIONS = [
    ('data_input', 'Access data upload'),
    ('data_quality', 'Run data quality checks'),
    ('analysis', 'Run analytics'),
    ('risk_prediction', 'Run risk prediction'),
    ('dashboard', 'View dashboards'),
    ('ai_report', 'Generate AI reports'),
    ('logframe', 'Manage logframes'),
    ('data_responsibility', 'Data responsibility'),
    ('user_management', 'Manage users'),
    ('settings', 'Access settings'),
    ('audit_view', 'View audit logs'),
    ('hdx', 'HDX integration'),
    ('three_w', '3W tracking'),
    ('budget', 'Budget tracking'),
]

ROLE_PERMISSIONS = {
    'Admin': [perm for perm, _ in PERMISSIONS],
    'Staff/Manager': ['data_input', 'data_quality', 'analysis', 'dashboard', 'ai_report', 'logframe', 'hdx', 'three_w', 'budget', 'settings'],
    'Moderator': ['data_quality', 'analysis', 'dashboard', 'ai_report', 'logframe', 'audit_view'],
    'Programme Manager': ['data_input', 'data_quality', 'analysis', 'risk_prediction', 'dashboard', 'ai_report', 'logframe', 'hdx', 'three_w', 'budget'],
    'M&E Officer': ['data_input', 'data_quality', 'analysis', 'logframe', 'hdx', 'three_w'],
    'Standard User': ['data_input', 'data_quality', 'analysis', 'dashboard', 'ai_report'],
    'Donor': ['dashboard', 'ai_report'],
}

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PHONE_REGEX = re.compile(r'^\+?[0-9\-\s]{7,20}$')


def get_connection():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


def validate_phone(phone: str) -> bool:
    if not phone:
        return True
    return bool(PHONE_REGEX.match(phone.strip()))


def validate_full_name(full_name: str) -> bool:
    return bool(full_name and len(full_name.strip()) >= 3)


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 10:
        return False, 'Password must be at least 10 characters long.'
    if password.islower() or password.isupper():
        return False, 'Password should include both upper and lower case characters.'
    if not any(char.isdigit() for char in password):
        return False, 'Password should include at least one number.'
    if not any(char in '!@#$%^&*()-_=+[]{}|;:,<.>/?' for char in password):
        return False, 'Password should include at least one special character.'
    return True, ''


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PASSWORD_HASH_ITERATIONS, dklen=64)
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, stored_hex = password_hash.split('$')
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(stored_hex)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(iterations), dklen=64)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def _slugify_username(full_name: str, email: str) -> str:
    base = re.sub(r'[^a-z0-9]+', '', full_name.strip().lower()) or normalize_email(email).split('@')[0]
    base = base[:30]
    conn = get_connection()
    cursor = conn.cursor()
    candidate = base
    suffix = 1
    while True:
        cursor.execute('SELECT 1 FROM users WHERE username = ?', (candidate,))
        if not cursor.fetchone():
            conn.close()
            return candidate
        suffix += 1
        candidate = f"{base}{suffix}"


def _get_role_id(role_name: str) -> Optional[int]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM roles WHERE name = ?', (role_name,))
    row = cursor.fetchone()
    conn.close()
    return row['id'] if row else None


def _get_user_row_by_email_or_username(identifier: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ? OR username = ?', (normalize_email(identifier), identifier.strip()))
    row = cursor.fetchone()
    conn.close()
    return row


def _get_user_roles(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id = r.id WHERE ur.user_id = ?', (user_id,))
    roles = [row['name'] for row in cursor.fetchall()]
    conn.close()
    return roles


def _get_primary_role(user_id: int) -> str:
    roles = _get_user_roles(user_id)
    return roles[0] if roles else 'Standard User'


def has_permission(role: str, permission: str) -> bool:
    if not role or not permission:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM permissions p
        JOIN role_permissions rp ON rp.permission_id = p.id
        JOIN roles r ON r.id = rp.role_id
        WHERE r.name = ? AND p.name = ?
    ''', (role, permission))
    allowed = cursor.fetchone() is not None
    conn.close()
    return allowed


def require_permission(role: str, permission: str) -> bool:
    if permission is None:
        return True
    if has_permission(role, permission):
        return True
    raise PermissionError(f"Role '{role}' does not have permission '{permission}'.")


def is_email_registered(email: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE email = ?', (normalize_email(email),))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def _parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        try:
            return datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None


def get_user_by_session_token(session_token: str):
    if not session_token:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.full_name, u.email, u.phone, u.org_name,
               u.email_verified, u.is_active, u.is_suspended, u.is_banned, u.last_login
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.session_token = ?
          AND s.expires_at > ?
          AND u.is_active = 1
          AND u.is_suspended = 0
          AND u.is_banned = 0
          AND u.email_verified = 1
    ''', (session_token, _now().strftime('%Y-%m-%d %H:%M:%S')))
    user = cursor.fetchone()
    conn.close()
    if not user:
        return None
    sanitized = dict(user)
    sanitized['role'] = _get_primary_role(sanitized['id'])
    return sanitized


def logout(session_token: str) -> bool:
    if not session_token:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
    changed = cursor.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def _create_session(user_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    token = secrets.token_hex(SESSION_TOKEN_BYTES)
    refresh_token = secrets.token_hex(REFRESH_TOKEN_BYTES)
    expires_at = _now() + timedelta(hours=SESSION_EXPIRE_HOURS)
    refresh_expires_at = _now() + timedelta(days=REFRESH_EXPIRE_DAYS)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sessions (user_id, session_token, refresh_token, expires_at, refresh_expires_at, ip_address, user_agent) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                   (user_id, token, refresh_token, expires_at.strftime('%Y-%m-%d %H:%M:%S'), refresh_expires_at.strftime('%Y-%m-%d %H:%M:%S'), ip_address or '', user_agent or ''))
    conn.commit()
    conn.close()
    return token, refresh_token, expires_at


def login(identifier: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    if not identifier or not password:
        return False, 'Enter both email/username and password.'
    user_row = _get_user_row_by_email_or_username(identifier)
    if not user_row:
        return False, 'Invalid credentials.'
    user_id = user_row['id']
    
    if not verify_password(password, user_row['password_hash']):
        return False, 'Invalid credentials.'
    
    token, refresh_token, expires_at = _create_session(user_id, ip_address, user_agent)
    primary_role = _get_primary_role(user_id)
    return True, {
        'id': user_id,
        'username': user_row['username'],
        'full_name': user_row['full_name'],
        'email': user_row['email'],
        'role': primary_role,
        'org_name': user_row['org_name'],
        'token': token,
        'refresh_token': refresh_token,
        'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S'),
        'email_verified': bool(user_row['email_verified']),
    }


def register_user(full_name: str, email: str, password: str, confirm_password: str, role: str = 'Standard User', 
                  phone: Optional[str] = None, terms_agreed: bool = False, honeypot: str = '', invite_code: Optional[str] = None):
    if honeypot:
        return False, 'Spam detected.'
    if not terms_agreed:
        return False, 'You must agree to the terms and conditions.'
    if not validate_full_name(full_name):
        return False, 'Please enter a valid full name.'
    if not validate_email(email):
        return False, 'Enter a valid email address.'
    if password != confirm_password:
        return False, 'Passwords do not match.'
    valid, message = validate_password_strength(password)
    if not valid:
        return False, message
    if is_email_registered(email):
        return False, 'An account with this email already exists.'
    
    username = _slugify_username(full_name, email)
    password_hash = hash_password(password)
    email_normalized = normalize_email(email)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, full_name, email, phone, password_hash, is_active, email_verified) VALUES (?, ?, ?, ?, ?, 1, 1)',
                      (username, full_name.strip(), email_normalized, phone.strip() if phone else None, password_hash))
        user_id = cursor.lastrowid
        role_id = _get_role_id(role)
        if role_id:
            cursor.execute('INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)', (user_id, role_id))
        conn.commit()
        return True, f'Account created successfully!'
    except Exception as e:
        conn.rollback()
        return False, f'Unable to create account: {str(e)}'
    finally:
        conn.close()


def request_password_reset(email: str):
    return False, 'Password reset not configured in demo mode.', None


def verify_email(token: str):
    return True, 'Email verified successfully.'


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.full_name, u.email, u.phone, u.org_name, 
               u.is_active, u.is_suspended, u.is_banned, u.email_verified, 
               u.created_at, u.last_login,
               COALESCE(
                   (SELECT r.name FROM roles r 
                    JOIN user_roles ur ON ur.role_id = r.id 
                    WHERE ur.user_id = u.id LIMIT 1),
                   'Standard User'
               ) as role
        FROM users u 
        ORDER BY u.created_at DESC
    ''')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def update_user_role(user_id: int, new_role: str, assigned_by: Optional[int] = None):
    role_id = _get_role_id(new_role)
    if not role_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))
    cursor.execute('INSERT INTO user_roles (user_id, role_id, assigned_by) VALUES (?, ?, ?)', (user_id, role_id, assigned_by))
    conn.commit()
    conn.close()
    return True


def deactivate_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def activate_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def change_password(user_id: int, old_password: str, new_password: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if not row or not verify_password(old_password, row['password_hash']):
        conn.close()
        return False, 'Current password is incorrect.'
    valid, message = validate_password_strength(new_password)
    if not valid:
        conn.close()
        return False, message
    new_hash = hash_password(new_password)
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user_id))
    conn.commit()
    conn.close()
    return True, 'Password changed successfully.'


def create_user(username: str, email: str, password: str, role: str, org_name: Optional[str] = None, 
                phone: Optional[str] = None, created_by: Optional[int] = None):
    if is_email_registered(email):
        return False, 'Email already exists.'
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = hash_password(password)
    cursor.execute('INSERT INTO users (username, full_name, email, phone, org_name, password_hash, is_active, email_verified) VALUES (?, ?, ?, ?, ?, ?, 1, 1)',
                  (username.strip(), username.strip(), normalize_email(email), phone.strip() if phone else None, org_name.strip() if org_name else None, password_hash))
    user_id = cursor.lastrowid
    role_id = _get_role_id(role)
    if role_id:
        cursor.execute('INSERT INTO user_roles (user_id, role_id, assigned_by) VALUES (?, ?, ?)', (user_id, role_id, created_by))
    conn.commit()
    conn.close()
    return True, f'User {username} created successfully.'


def get_role_description(role_name: str) -> str:
    for name, description in ROLES:
        if name == role_name:
            return description
    return 'No description available.'


def create_admin_invite(email: str, role: str, expires_hours: int = 48, created_by: Optional[int] = None):
    return True, 'Invite created successfully.', 'test-token-123'


def get_admin_invites():
    return []


def revoke_admin_invite(invite_id: int, revoked_by: Optional[int] = None):
    return True


def initialise_auth_tables():
    print("Initializing authentication tables...")
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER,
            permission_id INTEGER,
            PRIMARY KEY (role_id, permission_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            org_name TEXT,
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            is_suspended INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            email_verified INTEGER DEFAULT 0,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            role_id INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_by INTEGER,
            PRIMARY KEY (user_id, role_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT UNIQUE NOT NULL,
            refresh_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            refresh_expires_at TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT
        )
    ''')
    
    for role_name, description in ROLES:
        cursor.execute('INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)', (role_name, description))
    
    for perm_name, description in PERMISSIONS:
        cursor.execute('INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)', (perm_name, description))
    
    for role_name, perms in ROLE_PERMISSIONS.items():
        cursor.execute('SELECT id FROM roles WHERE name = ?', (role_name,))
        role_row = cursor.fetchone()
        if role_row:
            role_id = role_row['id']
            for perm_name in perms:
                cursor.execute('SELECT id FROM permissions WHERE name = ?', (perm_name,))
                perm_row = cursor.fetchone()
                if perm_row:
                    cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (role_id, perm_row['id']))
    
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        admin_password = os.environ.get('PAMOJADATA_ADMIN_PASSWORD', 'Peternyasiri@2030!')
        admin_username = os.environ.get('PAMOJADATA_ADMIN_USER', 'admin')
        admin_email = os.environ.get('PAMOJADATA_ADMIN_EMAIL', 'admin@pamojadata.org')
        admin_full_name = os.environ.get('PAMOJADATA_ADMIN_FULL_NAME', 'Pamoja Admin')
        
        admin_hash = hash_password(admin_password)
        
        cursor.execute('''
            INSERT INTO users (username, full_name, email, password_hash, is_active, email_verified)
            VALUES (?, ?, ?, ?, 1, 1)
        ''', (admin_username, admin_full_name, normalize_email(admin_email), admin_hash))
        
        user_id = cursor.lastrowid
        
        cursor.execute('SELECT id FROM roles WHERE name = ?', ('Admin',))
        role_row = cursor.fetchone()
        if role_row:
            cursor.execute('INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)', (user_id, role_row['id']))
        
        print(f'Admin user created: {admin_username} / {admin_password}')
    
    conn.commit()
    conn.close()
    print('Authentication database ready.')


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
