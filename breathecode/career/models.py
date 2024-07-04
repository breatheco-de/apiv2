from django.db import models


class Platform(models.Model):
    name = models.CharField(max_length=150)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class Position(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class ZyteProject(models.Model):
    zyte_api_key = models.CharField(max_length=150)
    zyte_api_deploy = models.CharField(max_length=50)
    zyte_api_spider_number = models.IntegerField(
        null=False, blank=False, help_text="This number is the one that corresponds when the ZYTE spider was created."
    )
    zyte_api_last_job_number = models.IntegerField(
        default=0, null=True, blank=True, help_text="(Optional field) Start at 0 but increase with each search."
    )

    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.platform} {self.zyte_api_key} {self.zyte_api_deploy} ({self.id})"


SYNCHED = "SYNCHED"
PENDING = "PENDING"
WARNING = "WARNING"
ERROR = "ERROR"
SPIDER_STATUS = (
    (SYNCHED, "Synched"),
    (PENDING, "Pending"),
    (WARNING, "Warning"),
    (ERROR, "Error"),
)


class Spider(models.Model):

    # num_spider = self.zyte_project.objects.filter(id=zyte_project)

    name = models.CharField(max_length=150)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=False, blank=False)
    job_search = models.CharField(max_length=150)
    loc_search = models.CharField(
        max_length=150, null=True, blank=True, help_text="This field may be optional on some platforms."
    )
    zyte_project = models.ForeignKey(ZyteProject, on_delete=models.CASCADE, null=False, blank=False)
    zyte_spider_number = models.IntegerField(
        default=0, null=True, blank=True, help_text="This number must be copy from ZYTE"
    )
    zyte_job_number = models.IntegerField(
        default=0, null=True, blank=True, help_text="Start at 0 but increase on each fetch"
    )
    zyte_fetch_count = models.IntegerField(default=0, help_text="The number of spider job excecutions to fetch")
    zyte_last_fetch_date = models.DateTimeField(null=True, blank=True)
    spider_last_run_status = models.CharField(max_length=15, choices=SPIDER_STATUS, default=PENDING)
    spider_last_run_desc = models.CharField(max_length=200, null=True, blank=True)
    sync_status = models.CharField(max_length=15, choices=SPIDER_STATUS, default=PENDING)
    sync_desc = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self):
        self.zyte_spider_number = self.zyte_project.zyte_api_spider_number
        self.zyte_job_number = self.zyte_project.zyte_api_last_job_number

    def __str__(self):
        return f"{self.name} ({self.id})"


class PositionAlias(models.Model):
    name = models.CharField(max_length=100)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class CareerTag(models.Model):
    slug = models.SlugField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.slug} ({self.id})"


class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class LocationAlias(models.Model):
    name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class Employer(models.Model):
    name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} {self.name} ({self.id})"


OPENED = "OPENED"
FILLED = "FILLED"
JOB_STATUS = (
    (OPENED, "Opened"),
    (FILLED, "Filled"),
)

FULLTIME = "Full-time"
INTERNSHIP = "Internship"
PARTTIME = "Part-time"
TEMPORARY = "Temporary"
CONTRACT = "Contract"
JOB_TYPE = (
    (FULLTIME, "Full-time"),
    (INTERNSHIP, "Internship"),
    (PARTTIME, "Part-time"),
    (TEMPORARY, "Temporary"),
    (CONTRACT, "Contract"),
)

USD = "USD"  # United States dollar
CRC = "CRC"  # Costa Rican colón
CLP = "CLP"  # Chilean peso
EUR = "EUR"  # Euro
UYU = "UYU"  # Uruguayan peso
CURRENCIES = (
    (USD, "USD"),
    (CRC, "CRC"),
    (CLP, "CLP"),
    (EUR, "EUR"),
    (UYU, "UYU"),
)


class Job(models.Model):
    title = models.CharField(max_length=150)
    spider = models.ForeignKey(Spider, on_delete=models.CASCADE, null=False, blank=False)
    published_date_raw = models.CharField(max_length=50)
    published_date_processed = models.DateTimeField(default=None, null=True, blank=True)
    status = models.CharField(max_length=15, choices=JOB_STATUS, default=OPENED)
    apply_url = models.URLField(max_length=500)
    currency = models.CharField(max_length=3, choices=CURRENCIES, default=USD, blank=True)
    min_salary = models.FloatField(null=True, blank=True)
    max_salary = models.FloatField(null=True, blank=True)
    salary = models.CharField(max_length=253, null=True, blank=True)
    job_description = models.TextField(null=True, blank=True)
    job_type = models.CharField(max_length=15, choices=JOB_TYPE, default=FULLTIME)
    remote = models.BooleanField(default=False, verbose_name="Remote")
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, null=True, blank=True)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, null=False, blank=False)
    career_tags = models.ManyToManyField(CareerTag, blank=True)
    locations = models.ManyToManyField(Location, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.title} ({self.id})"
