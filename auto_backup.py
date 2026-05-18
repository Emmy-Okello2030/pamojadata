import shutil
import logging
from datetime import datetime
from pathlib import Path

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(filename=log_dir / "backup.log", level=logging.INFO, format='%(asctime)s - %(message)s')

def backup_database():
    try:
        project_path = Path(__file__).parent
        source_path = project_path / "secure_data" / "pamojadata.db"
        if not source_path.exists():
            source_path = project_path / "data" / "pamojadata.db"
        if not source_path.exists():
            print("Database not found")
            return False
        backup_dir = project_path / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"pamojadata_backup_{timestamp}.db"
        shutil.copy2(str(source_path), str(backup_path))
        logging.info(f"Backup created: {backup_path.name}")
        print(f"Backup created: {backup_path.name}")
        backups = sorted(backup_dir.glob("pamojadata_backup_*.db"))
        while len(backups) > 30:
            backups.pop(0).unlink()
        return True
    except Exception as e:
        logging.error(f"Backup failed: {str(e)}")
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    backup_database()
