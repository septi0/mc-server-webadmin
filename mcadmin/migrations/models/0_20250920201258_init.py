from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "global_properties" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "key" VARCHAR(100) NOT NULL UNIQUE,
    "value" VARCHAR(255) NOT NULL
);
CREATE TABLE IF NOT EXISTS "instance_backups" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "instance_id" INT NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "type" VARCHAR(50) NOT NULL,
    "metadata" JSON NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_instance_ba_instanc_ecaf39" ON "instance_backups" ("instance_id");
CREATE TABLE IF NOT EXISTS "instance_datapacks" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "instance_id" INT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "enabled" INT NOT NULL DEFAULT 1,
    "added_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_instance_da_instanc_37f038" ON "instance_datapacks" ("instance_id");
CREATE TABLE IF NOT EXISTS "instance_mods" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "instance_id" INT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "enabled" INT NOT NULL DEFAULT 1,
    "added_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_instance_mo_instanc_7488d2" ON "instance_mods" ("instance_id");
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
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
