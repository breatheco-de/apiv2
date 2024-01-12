from asgiref.sync import sync_to_async
from django.db import models

# Create your models here.

# models.Model.objects.afilter = sync_to_async(models.Model.objects.filter)
models.Manager.afilter = sync_to_async(models.Manager.filter)
# class BaseModel(models.Model):
#     class Meta:
#         abstract = True

#     objects = models.Manager()

#     def __str__(self):
#         return str(self.id)


class MyModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField()
