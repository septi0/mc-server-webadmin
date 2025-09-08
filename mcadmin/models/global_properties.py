from tortoise import fields, models

class GlobalProperties(models.Model):
    id = fields.IntField(pk=True)
    key = fields.CharField(max_length=100, unique=True)
    value = fields.CharField(max_length=255)

    class Meta:
        table = "global_properties"

    def __str__(self):
        return self.key
