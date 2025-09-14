from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "global_properties" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "key" VARCHAR(100) NOT NULL UNIQUE,
    "value" VARCHAR(255) NOT NULL
);
INSERT OR IGNORE INTO global_properties (key, value) VALUES
    ('difficulty', 'normal'),
    ('gamemode', 'survival'),
    ('max-players', '20');
CREATE TABLE IF NOT EXISTS "mcadmin" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "key" VARCHAR(100) NOT NULL UNIQUE,
    "value" VARCHAR(255) NOT NULL
);
CREATE TABLE IF NOT EXISTS "sessions" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "token" VARCHAR(255) NOT NULL UNIQUE,
    "user_id" INT NOT NULL,
    "ip" VARCHAR(45) NOT NULL,
    "user_agent" VARCHAR(255) NOT NULL,
    "device" VARCHAR(255),
    "data" TEXT NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiry" TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_sessions_user_id_80072d" ON "sessions" ("user_id");
CREATE TABLE IF NOT EXISTS "users" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "username" VARCHAR(100) NOT NULL UNIQUE,
    "password" VARCHAR(128) NOT NULL,
    "role" VARCHAR(50) NOT NULL DEFAULT 'user',
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "instances" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "server_version" VARCHAR(50) NOT NULL,
    "server_type" VARCHAR(50) NOT NULL DEFAULT 'vanilla',
    "properties" JSON NOT NULL,
    "active" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
