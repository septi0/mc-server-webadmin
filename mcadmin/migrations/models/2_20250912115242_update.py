from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "world_backups" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "world_id" INT NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "type" VARCHAR(50) NOT NULL,
    "metadata" JSON NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_world_backu_world_i_117735" ON "world_backups" ("world_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "world_backups";"""
