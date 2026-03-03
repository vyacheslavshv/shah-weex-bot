from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True)
    username = fields.CharField(max_length=255, null=True)
    first_name = fields.CharField(max_length=255, null=True)
    join_time = fields.DatetimeField()
    status = fields.CharField(max_length=20, default="trial")
    weex_uid = fields.CharField(max_length=100, null=True, unique=True)
    verified_time = fields.DatetimeField(null=True)
    last_trade_check = fields.DatetimeField(null=True)
    verify_attempts = fields.IntField(default=0)
    last_verify_attempt = fields.DatetimeField(null=True)
    bot_started = fields.BooleanField(default=False)

    class Meta:
        table = "users"


class RelayMessage(Model):
    id = fields.IntField(pk=True)
    forwarded_msg_id = fields.BigIntField(index=True)
    user_telegram_id = fields.BigIntField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "relay_messages"
