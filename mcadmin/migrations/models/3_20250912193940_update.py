from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "world_datapacks" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "world_id" INT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "added_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_world_datap_world_i_f6e74d" ON "world_datapacks" ("world_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "world_datapacks";"""
