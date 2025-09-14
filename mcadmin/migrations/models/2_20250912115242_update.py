from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "instance_backups" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "instance_id" INT NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "type" VARCHAR(50) NOT NULL,
    "metadata" JSON NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_instance_backups_instance_id" ON "instance_backups" ("instance_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "instance_backups";"""
