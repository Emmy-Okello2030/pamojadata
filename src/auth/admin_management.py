"""
Admin Management Module
Provides admin-specific operations for user management, role assignment, and system administration.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from src.database.db import DB_PATH as DEFAULT_DB_PATH
from src.auth.auth import (
    get_connection, _now, _record_audit, normalize_email,
    validate_email, hash_password, _get_role_id, _get_primary_role
)

def get_all_users_with_roles() -> List[Dict[str, Any]]:
    """
    Retrieve all users with their assigned roles.
    
    Returns:
        List of user dictionaries with role information
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT
            u.id, u.username, u.full_name, u.email, u.phone, u.org_name,
            u.is_active, u.is_suspended, u.is_banned, u.email_verified,
            u.created_at, u.last_login,
            GROUP_CONCAT(r.name, ', ') as roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def search_users(query: str) -> List[Dict[str, Any]]:
    """
    Search users by username, email, or full name.
    
    Args:
        query: Search query string
    
    Returns:
        List of matching users
    """
    conn = get_connection()
    cursor = conn.cursor()
    search_term = f"%{query.lower()}%"
    cursor.execute('''
        SELECT DISTINCT
            u.id, u.username, u.full_name, u.email, u.phone, u.org_name,
            u.is_active, u.is_suspended, u.is_banned, u.email_verified,
            u.created_at, u.last_login,
            GROUP_CONCAT(r.name, ', ') as roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        WHERE LOWER(u.username) LIKE ? OR LOWER(u.email) LIKE ? OR LOWER(u.full_name) LIKE ?
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''', (search_term, search_term, search_term))
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def suspend_user(user_id: int, admin_id: Optional[int] = None, reason: str = "") -> bool:
    """
    Suspend a user account (prevents login).
    
    Args:
        user_id: User ID to suspend
        admin_id: Admin performing the action
        reason: Reason for suspension
    
    Returns:
        True if successful
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_suspended = 1, updated_at = ? WHERE id = ?',
                   (_now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
    conn.commit()
    conn.close()
    _record_audit(admin_id, 'suspend_user', f'user_id={user_id} reason={reason}')
    return True


def unsuspend_user(user_id: int, admin_id: Optional[int] = None) -> bool:
    """
    Unsuspend a user account.
    
    Args:
        user_id: User ID to unsuspend
        admin_id: Admin performing the action
    
    Returns:
        True if successful
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_suspended = 0, updated_at = ? WHERE id = ?',
                   (_now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
    conn.commit()
    conn.close()
    _record_audit(admin_id, 'unsuspend_user', f'user_id={user_id}')
    return True


def ban_user(user_id: int, admin_id: Optional[int] = None, reason: str = "") -> bool:
    """
    Ban a user account (permanent suspension).
    
    Args:
        user_id: User ID to ban
        admin_id: Admin performing the action
        reason: Reason for ban
    
    Returns:
        True if successful
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1, is_active = 0, updated_at = ? WHERE id = ?',
                   (_now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
    conn.commit()
    conn.close()
    _record_audit(admin_id, 'ban_user', f'user_id={user_id} reason={reason}')
    return True


def unban_user(user_id: int, admin_id: Optional[int] = None) -> bool:
    """
    Unban a user account.
    
    Args:
        user_id: User ID to unban
        admin_id: Admin performing the action
    
    Returns:
        True if successful
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 0, is_active = 1, updated_at = ? WHERE id = ?',
                   (_now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
    conn.commit()
    conn.close()
    _record_audit(admin_id, 'unban_user', f'user_id={user_id}')
    return True


def delete_user(user_id: int, admin_id: Optional[int] = None) -> bool:
    """
    Permanently delete a user account and all associated data.
    
    Args:
        user_id: User ID to delete
        admin_id: Admin performing the action
    
    Returns:
        True if successful
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Delete related records
    cursor.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM login_attempts WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM password_resets WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM email_verifications WHERE user_id = ?', (user_id,))
    
    # Delete user
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    conn.commit()
    conn.close()
    _record_audit(admin_id, 'delete_user', f'user_id={user_id}')
    return True


def get_user_activity(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get audit logs for a specific user.
    
    Args:
        user_id: User ID
        limit: Maximum number of records to return
    
    Returns:
        List of audit log entries
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, action, details, ip_address, created_at
        FROM audit_logs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs


def get_login_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get login history for a specific user.
    
    Args:
        user_id: User ID
        limit: Maximum number of records to return
    
    Returns:
        List of login attempt records
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, identifier, ip_address, successful, reason, created_at
        FROM login_attempts
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    attempts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return attempts


def get_system_statistics() -> Dict[str, Any]:
    """
    Get system-wide statistics.
    
    Returns:
        Dictionary of statistics
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM users')
    total_users = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_active = 1 AND is_suspended = 0 AND is_banned = 0')
    active_users = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_suspended = 1')
    suspended_users = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_banned = 1')
    banned_users = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE email_verified = 0')
    unverified_users = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM sessions WHERE expires_at > ?',
                   (_now().strftime('%Y-%m-%d %H:%M:%S'),))
    active_sessions = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM login_attempts WHERE successful = 0 AND created_at > datetime("now", "-24 hours")')
    failed_logins_24h = cursor.fetchone()['count']
    
    cursor.execute('''
        SELECT r.name, COUNT(ur.user_id) as count
        FROM roles r
        LEFT JOIN user_roles ur ON r.id = ur.role_id
        GROUP BY r.name
    ''')
    role_distribution = {row['name']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'suspended_users': suspended_users,
        'banned_users': banned_users,
        'unverified_users': unverified_users,
        'active_sessions': active_sessions,
        'failed_logins_24h': failed_logins_24h,
        'role_distribution': role_distribution,
    }


def get_recent_activity(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get recent system-wide activity.
    
    Args:
        limit: Maximum number of records to return
    
    Returns:
        List of recent audit log entries
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, action, details, ip_address, created_at
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs


def get_failed_login_attempts(hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get failed login attempts in the last N hours.
    
    Args:
        hours: Number of hours to look back
        limit: Maximum number of records to return
    
    Returns:
        List of failed login attempts
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, identifier, ip_address, reason, created_at
        FROM login_attempts
        WHERE successful = 0 AND created_at > datetime("now", ? || " hours")
        ORDER BY created_at DESC
        LIMIT ?
    ''', (f'-{hours}', limit))
    attempts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return attempts
