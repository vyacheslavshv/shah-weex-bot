from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "relay_messages" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "forwarded_msg_id" BIGINT NOT NULL,
    "user_telegram_id" BIGINT NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_relay_messa_forward_71a3a1" ON "relay_messages" ("forwarded_msg_id");
CREATE TABLE IF NOT EXISTS "users" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "telegram_id" BIGINT NOT NULL UNIQUE,
    "username" VARCHAR(255),
    "first_name" VARCHAR(255),
    "join_time" TIMESTAMP NOT NULL,
    "status" VARCHAR(20) NOT NULL DEFAULT 'trial',
    "weex_uid" VARCHAR(100) UNIQUE,
    "verified_time" TIMESTAMP,
    "last_trade_check" TIMESTAMP,
    "verify_attempts" INT NOT NULL DEFAULT 0,
    "last_verify_attempt" TIMESTAMP,
    "bot_started" INT NOT NULL DEFAULT 0
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


MODELS_STATE = (
    "eJztmVtv2jAUgP8KylMndRUFWtjeoGMrU4GppdvUqrJMYoKHY7PYWYsq/vtsJyHkAgPKde"
    "INzsXx+Q7nHMe8Gg6zEOFnt4jAURNxDm1kfMy9GhQ66kOm/jRnwOEw0iqBgF2iHVxlCRzf"
    "VKtglwsXmkJqe5BwJEUW4qaLhwIzKqXUI0QJmSkNMbUjkUfxbw8BwWwk+siViscnKcbUQi"
    "9y8eDrcAB6GBErtnFsqWdrORCjoZY1qPisDdXTusBkxHNoZDwciT6jE2tMhZLaiCIXCqSW"
    "F66ntq92F8QbRuTvNDLxtzjlY6Ee9IiYCndBBiajip/cDdcB6gS9L5yXyqVK8bJUkSZ6Jx"
    "NJeeyHF8XuO2oCrY4x1noooG+hMUbcesx9hq6FLOBwG2RRrGF7Jsgs739jDSHO4xoKNg32"
    "Q6FQLJYL+eJl5aJULl9U8hPCadU81LXGF0VbGjD56/eLI8Qf4fY4coFABNkudJbGneW9Kd"
    "xR7R4yb9NFigKAIk36k9QI7KBs1nHPBGUrcD0LP+wpcxmD1aZkFJTPHJydRrN+16k2v6lI"
    "HM5/E42o2qkrTUFLRwnpyeW7OP/JIrkfjc51Tn3NPbRbdU2QcWG7+omRXefBUHuCnmCAsm"
    "cAralKD6UhmLFq/r3BVBtTgi40B6oHgZSGFdgs27TKKThJCaRypFkBXLXNYDjecz2aUkNT"
    "y+cOS1W/xxl5cDNy5X69kVa9JZo7GIz6cwrwVR+6s8dh6JNgKwNagG1Abpsd2YEvgCBqi7"
    "76fV5czAH3vXp7dV29PZFWiT7bClQFXxcn2cMuF2BZlnGvI82Q5i+GJQecBXP++SHmeJjH"
    "hwM5LoRhp84L03nkAgqPL1MRkcdK1bBSvgyZEEiMtVVEfpGCyM+uh3yyHJ4RegFe1hycDX"
    "LaZy2NZeMTMAbxPL8IRWk1E6PWxTn+QS6Wy1krtZaU8xray/ab9//UXQiUw1PGZiFg9pE5"
    "WDajWf7HpO44qbrMRgAKgZyhyJgdM8/9GZ7bu6bJv/no/8YXqURZxGGsVBnpJY7FsePi6D"
    "IB5AnJVXhTKa0xRhCk2RlNeCYy2ZWum6qMZa9aFk9frd2+iWWu1ki88bbum7W6PCbolEkj"
    "LKZehPfkYqsqy8zsGxlXW4HmdN7lFoxsjrdb6zyNbvh2SzZXrra0xIl+ymV770Z7f1WgSm"
    "MJiIH5YQLcyEuRfKJANOOI8PWu3ZrxL03kkgB5T2WAjxY2xWmOYC6e9hPrHIoq6thQCeGd"
    "NKs/k1yvbtq15JxXC9R2PV7GfwGp3lXG"
)
