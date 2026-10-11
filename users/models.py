from django.db import models
from django.utils import timezone

class CustomerProfile(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255, default='সম্মানিত গ্রাহক')
    phone = models.CharField(max_length=32, db_index=True)
    email = models.EmailField(blank=True, null=True, db_index=True)
    district = models.CharField(max_length=128, default='Dhaka')
    thana = models.CharField(max_length=128, default='Mirpur')
    fullAddress = models.TextField(blank=True)
    password = models.CharField(max_length=255, blank=True, default='')
    createdAt = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.phone})"
