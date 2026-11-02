"""Delete only the local synthetic SQLite database and recreate the sample data."""
from pathlib import Path
from .database import DB_PATH
from .seed import seed

if __name__ == '__main__':
    print('WARNING: reset deletes all local synthetic demo data.')
    reply = input('Enter RESET to confirm: ')
    if reply != 'RESET':
        print('Cancelled.')
    else:
        for suffix in ('', '-wal', '-shm'):
            Path(str(DB_PATH)+suffix).unlink(missing_ok=True)
        seed()
        print('Demo database reinitialized.')
