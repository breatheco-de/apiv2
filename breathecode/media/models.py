from django.contrib.auth.models import User
from django.db import models

from breathecode.admissions.models import Academy

__all__ = ["Category", "Media", "MediaResolution"]


class Category(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class Media(models.Model):
    slug = models.SlugField(max_length=150, unique=True)
    name = models.CharField(max_length=150)
    mime = models.CharField(max_length=60)
    url = models.URLField(max_length=255)
    thumbnail = models.URLField(max_length=255, blank=True, null=True)
    hash = models.CharField(max_length=64)
    hits = models.IntegerField(default=0)

    categories = models.ManyToManyField(Category, blank=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id} - {self.slug})"


class MediaResolution(models.Model):
    hash = models.CharField(max_length=64)
    width = models.IntegerField()
    height = models.IntegerField()
    hits = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.hash} ({self.width}x{self.height})"


class Chunk(models.Model):

    # class Provider(models.TextChoices):
    #     GITHUB = "GITHUB", "GitHub"

    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="User who uploaded the file")
    academy = models.ForeignKey(
        Academy, on_delete=models.CASCADE, null=True, blank=True, help_text="Academy where the file was uploaded"
    )
    name = models.CharField(max_length=255)
    mime = models.CharField(max_length=60)

    chunk_index = models.PositiveIntegerField()
    total_chunks = models.PositiveIntegerField()

    # this section avoid errors when settings changed
    chunk_size = models.PositiveIntegerField(help_text="Size of each chunk in bytes")
    # max_chucks = models.PositiveIntegerField(help_text="Maximum number of chunks allowed per file")
    bucket = models.CharField(max_length=255)
    operation_type = models.CharField(max_length=60)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    @property
    def file_name(self) -> str:
        name = f"{self.user.username}-{self.name}-{self.mime.split('/')[1]}-{self.chunk_index}-{self.total_chunks}-{self.chunk_size}"
        if self.academy:
            name = f"{self.academy.slug}-{name}"

        return name


class File(models.Model):

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        TRANSFERRING = "TRANSFERRING", "Transferring"
        TRANSFERRED = "TRANSFERRED", "Transferred"

    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="User who uploaded the file")
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text="Academy where the file was uploaded")

    name = models.CharField(max_length=255)
    mime = models.CharField(max_length=60)

    hash = models.CharField(max_length=64)
    size = models.PositiveIntegerField(null=True, blank=True)

    # this section avoid errors when settings changed
    bucket = models.CharField(max_length=255)
    operation_type = models.CharField(max_length=60)

    meta = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Metadata associated with the file, used for schedule the transfer",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    @property
    def file_name(self) -> str:
        return self.hash
