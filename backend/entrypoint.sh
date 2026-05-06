#!/bin/bash
set -e

echo "[backend] Waiting for PostgreSQL..."
for i in $(seq 1 30); do
    if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" 2>/dev/null; then
        echo "[backend] PostgreSQL is ready"
        break
    fi
    echo "[backend] Waiting for PostgreSQL... attempt $i/30"
    sleep 2
done

echo "[backend] Running database migrations..."
alembic upgrade head

echo "[backend] Seeding admin user..."
python3 - << 'PYEOF'
import asyncio
import os
import sys

sys.path.insert(0, '.')

async def seed():
    try:
        from app.core.database import AsyncSessionLocal
        from app.core.security import hash_password
        from app.models.user import User
        from sqlalchemy.future import select

        admin_email = os.getenv('ADMIN_EMAIL', 'admin@upi.ai')
        admin_password = os.getenv('ADMIN_PASSWORD')

        if not admin_password or admin_password.startswith('CHANGE_ME'):
            print('[backend] Skipping admin seed: ADMIN_PASSWORD not set or using default')
            return

        async with AsyncSessionLocal() as db:
            r = await db.execute(select(User).where(User.email == admin_email))
            if not r.scalar_one_or_none():
                db.add(User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    full_name='UPI Admin',
                    is_superuser=True,
                    is_active=True,
                ))
                await db.commit()
                print(f'[backend] Admin user created: {admin_email}')
            else:
                print(f'[backend] Admin user already exists: {admin_email}')
    except Exception as e:
        print(f'[backend] Seed error (non-fatal): {e}')

asyncio.run(seed())
PYEOF

echo "[backend] Starting uvicorn with 2 workers..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --loop uvloop
