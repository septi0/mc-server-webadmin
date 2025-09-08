from tortoise import fields, models

class Sessions(models.Model):
    id = fields.IntField(pk=True)
    token = fields.CharField(max_length=255, unique=True)
    user_id = fields.IntField(index=True)
    ip = fields.CharField(max_length=45)
    user_agent = fields.CharField(max_length=255)
    device = fields.CharField(max_length=255, null=True)
    data = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    expiry = fields.DatetimeField(null=True)

    class Meta:
        table = "sessions"

    def __str__(self):
        return str(self.id)
