from tortoise import fields, models

class WorldDatapacks(models.Model):
    id = fields.IntField(pk=True)
    world_id = fields.IntField(index=True)
    name = fields.CharField(max_length=255)
    added_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "world_datapacks"

    def __str__(self):
        return str(self.id)
