from tortoise import fields, models

class AppConfig(models.Model):
    id = fields.IntField(pk=True)
    key = fields.CharField(max_length=100, unique=True)
    value = fields.CharField(max_length=255)

    class Meta:
        table = "app_config"

    def __str__(self):
        return self.key
