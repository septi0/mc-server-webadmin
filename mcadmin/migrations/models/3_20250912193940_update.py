from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "instance_datapacks" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "instance_id" INT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "added_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_instance_datapacks_instance_id" ON "instance_datapacks" ("instance_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "instance_datapacks";"""
