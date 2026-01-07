from tortoise import fields, models

class OIDCProviders(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    default = fields.BooleanField(default=False)
    allow_registration = fields.BooleanField(default=False)
    auto_launch = fields.BooleanField(default=False)
    user_claim = fields.CharField(max_length=100)
    config = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "oidc_providers"

    def __str__(self):
        return self.name
