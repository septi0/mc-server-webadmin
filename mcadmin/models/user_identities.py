from tortoise import fields, models

class UserIdentities(models.Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    provider_id = fields.IntField()
    sub = fields.CharField(max_length=200)
    added_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_identities"
        unique_together = (("user_id", "provider_id", "sub"),)

    def __str__(self):
        return str(self.user_id)
