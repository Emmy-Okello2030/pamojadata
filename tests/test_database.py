import sqlite3

from src.database import db


def test_initialise_database_creates_tables(tmp_path, monkeypatch):
    db_file = tmp_path / "test_db.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_file))

    db.initialise_database()

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    assert "organisations" in tables
    assert "programmes" in tables
    assert "indicators" in tables
    assert "reports" in tables


def test_save_report_with_nullable_programme(tmp_path, monkeypatch):
    db_file = tmp_path / "test_db.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_file))
    db.initialise_database()

    db.save_report(programme_id=None, report_period="Q1 2026", donor_type="General", narrative="Test narrative")
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT programme_id, report_period, donor_type, narrative FROM reports")
    row = cursor.fetchone()
    conn.close()

    assert row == (None, "Q1 2026", "General", "Test narrative")
