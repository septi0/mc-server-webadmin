from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "world_mods" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "world_id" INT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "added_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_world_mods_world_i_0634a3" ON "world_mods" ("world_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "world_mods";"""
