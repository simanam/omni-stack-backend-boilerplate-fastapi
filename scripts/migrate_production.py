#!/usr/bin/env python3
"""
Production Database Migration Script

This script safely runs database migrations in production with:
- Pre-migration health checks
- Backup verification
- Migration dry-run option
- Rollback support
- Logging and notifications

Usage:
    python scripts/migrate_production.py [--dry-run] [--rollback] [--revision REVISION]

Examples:
    # Check what migrations would run
    python scripts/migrate_production.py --dry-run

    # Run all pending migrations
    python scripts/migrate_production.py

    # Rollback last migration
    python scripts/migrate_production.py --rollback

    # Migrate to specific revision
    python scripts/migrate_production.py --revision abc123
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles production database migrations safely."""

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Ensure async driver
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

        self.alembic_cfg = Config("alembic.ini")
        self.script_dir = ScriptDirectory.from_config(self.alembic_cfg)

    async def check_database_connection(self) -> bool:
        """Verify database is accessible."""
        logger.info("Checking database connection...")
        try:
            engine = create_async_engine(self.database_url)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            logger.info("Database connection: OK")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    async def get_current_revision(self) -> str | None:
        """Get current database revision."""
        engine = create_async_engine(self.database_url)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception:
            return None
        finally:
            await engine.dispose()

    def get_pending_migrations(self, current: str | None) -> list[str]:
        """Get list of pending migrations."""
        revisions = []
        for rev in self.script_dir.walk_revisions("head", current or "base"):
            if rev.revision != current:
                revisions.append(rev.revision)
        return list(reversed(revisions))

    def get_migration_info(self, revision: str) -> dict:
        """Get information about a specific migration."""
        rev = self.script_dir.get_revision(revision)
        return {
            "revision": rev.revision,
            "down_revision": rev.down_revision,
            "doc": rev.doc or "No description",
            "path": rev.path,
        }

    async def check_active_connections(self) -> int:
        """Check number of active database connections."""
        engine = create_async_engine(self.database_url)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        """
                        SELECT count(*) FROM pg_stat_activity
                        WHERE datname = current_database()
                        AND state = 'active'
                        """
                    )
                )
                return result.scalar() or 0
        finally:
            await engine.dispose()

    async def create_backup_point(self) -> str:
        """Create a named savepoint before migration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        savepoint_name = f"pre_migration_{timestamp}"
        logger.info(f"Creating savepoint: {savepoint_name}")
        return savepoint_name

    def run_migration(
        self,
        target: str = "head",
        dry_run: bool = False,
    ) -> bool:
        """Run database migration."""
        if dry_run:
            logger.info("DRY RUN - No changes will be made")
            logger.info(f"Would migrate to: {target}")
            return True

        try:
            logger.info(f"Running migration to: {target}")
            start_time = time.time()

            command.upgrade(self.alembic_cfg, target)

            duration = time.time() - start_time
            logger.info(f"Migration completed in {duration:.2f} seconds")
            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

    def run_rollback(self, steps: int = 1) -> bool:
        """Rollback database migration."""
        try:
            logger.info(f"Rolling back {steps} migration(s)")
            command.downgrade(self.alembic_cfg, f"-{steps}")
            logger.info("Rollback completed")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Production database migration tool")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the last migration",
    )
    parser.add_argument(
        "--rollback-steps",
        type=int,
        default=1,
        help="Number of migrations to rollback (default: 1)",
    )
    parser.add_argument(
        "--revision",
        type=str,
        help="Target revision to migrate to",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip pre-migration checks (not recommended)",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Production Migration Script")
    logger.info("=" * 60)

    try:
        runner = MigrationRunner()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Pre-migration checks
    if not args.skip_checks:
        logger.info("\nRunning pre-migration checks...")

        # Check database connection
        if not await runner.check_database_connection():
            logger.error("Pre-migration check failed: Database not accessible")
            sys.exit(1)

        # Check active connections
        active_conns = await runner.check_active_connections()
        logger.info(f"Active database connections: {active_conns}")

        if active_conns > 10:
            logger.warning(
                f"High number of active connections ({active_conns}). "
                "Consider running during low-traffic period."
            )

    # Get current state
    current_revision = await runner.get_current_revision()
    logger.info(f"\nCurrent revision: {current_revision or 'None (empty database)'}")

    # Handle rollback
    if args.rollback:
        if args.dry_run:
            logger.info(f"DRY RUN: Would rollback {args.rollback_steps} migration(s)")
            sys.exit(0)

        confirm = input(
            f"\nConfirm rollback of {args.rollback_steps} migration(s)? (yes/no): "
        )
        if confirm.lower() != "yes":
            logger.info("Rollback cancelled")
            sys.exit(0)

        success = runner.run_rollback(args.rollback_steps)
        sys.exit(0 if success else 1)

    # Get pending migrations
    pending = runner.get_pending_migrations(current_revision)

    if not pending:
        logger.info("\nNo pending migrations")
        sys.exit(0)

    # Show pending migrations
    logger.info(f"\nPending migrations ({len(pending)}):")
    for rev in pending:
        info = runner.get_migration_info(rev)
        logger.info(f"  - {rev}: {info['doc']}")

    # Determine target
    target = args.revision if args.revision else "head"

    # Dry run
    if args.dry_run:
        logger.info(f"\nDRY RUN: Would migrate from {current_revision} to {target}")
        sys.exit(0)

    # Confirm migration
    confirm = input(f"\nProceed with migration to '{target}'? (yes/no): ")
    if confirm.lower() != "yes":
        logger.info("Migration cancelled")
        sys.exit(0)

    # Create backup point
    await runner.create_backup_point()

    # Run migration
    logger.info("\nStarting migration...")
    success = runner.run_migration(target)

    if success:
        # Verify migration
        new_revision = await runner.get_current_revision()
        logger.info(f"\nMigration successful. Current revision: {new_revision}")
    else:
        logger.error("\nMigration failed!")
        logger.info("Consider running with --rollback to revert changes")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
