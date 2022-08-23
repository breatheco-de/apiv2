# from django.db import models

# class Channel(models.Model):
#     kind = models.SlugField(unique=True, max_length=30, blank=True)

# class ChannelCache(models.Model):
#     kind = models.SlugField(unique=True, max_length=30, blank=True)
#     cache = models.SlugField(unique=True, max_length=30, blank=True)
#     channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
