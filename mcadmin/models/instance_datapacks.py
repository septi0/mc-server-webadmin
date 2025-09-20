from tortoise import fields, models

class InstanceDatapacks(models.Model):
    id = fields.IntField(pk=True)
    instance_id = fields.IntField(index=True)
    name = fields.CharField(max_length=255)
    enabled = fields.BooleanField(default=True)
    added_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "instance_datapacks"

    def __str__(self):
        return str(self.id)
