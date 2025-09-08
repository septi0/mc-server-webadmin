from tortoise import fields, models

class Users(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=100, unique=True)
    password = fields.CharField(max_length=128)
    role = fields.CharField(max_length=50, default="user")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"
        
    def __str__(self):
        return self.username