from django.db import models


class TimeSlot(models.Model):
    starting_at = models.DateTimeField()
    ending_at = models.DateTimeField()

    recurrent = models.BooleanField(default=True)
    recurrency_type = models.CharField(max_length=10,
                                       choices=RECURRENCY_TYPE,
                                       default=WEEKLY)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True