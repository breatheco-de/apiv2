from .models import FormEntry
from rest_framework import serializers

class PostFormEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = FormEntry
        exclude = ()