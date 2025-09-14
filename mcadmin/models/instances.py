from tortoise import fields, models

class Instances(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    server_version = fields.CharField(max_length=50)
    server_type = fields.CharField(max_length=50, default="vanilla")
    properties = fields.JSONField()
    active = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "instances"

    def __str__(self):
        return self.name
