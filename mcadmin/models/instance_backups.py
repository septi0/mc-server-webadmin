from tortoise import fields, models

class InstanceBackups(models.Model):
    id = fields.IntField(pk=True)
    instance_id = fields.IntField(index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    type = fields.CharField(max_length=50)
    metadata = fields.JSONField()

    class Meta:
        table = "instance_backups"

    def __str__(self):
        return str(self.id)
