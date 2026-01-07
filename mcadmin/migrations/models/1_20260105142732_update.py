from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "app_config" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "key" VARCHAR(100) NOT NULL UNIQUE,
    "value" VARCHAR(255) NOT NULL
);
INSERT OR IGNORE INTO app_config (key, value) VALUES ('auth_methods', 'local');
CREATE TABLE IF NOT EXISTS "oidc_providers" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "default" INT NOT NULL DEFAULT 0,
    "allow_registration" INT NOT NULL DEFAULT 0,
    "auto_launch" INT NOT NULL DEFAULT 0,
    "user_claim" VARCHAR(100) NOT NULL,
    "config" JSON NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "app_config";
        DROP TABLE IF EXISTS "oidc_providers";"""
