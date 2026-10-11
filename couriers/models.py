from django.db import models

class CourierConfig(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    logo = models.CharField(max_length=50, default='Truck')
    isActive = models.BooleanField(default=True)
    apiKey = models.CharField(max_length=255, blank=True, default='')
    secret = models.CharField(max_length=255, blank=True, default='')
    coverage = models.CharField(max_length=255, default='64 Districts & Sub-districts')
    codFeePercent = models.FloatField(default=1.0)
    insideDhakaRate = models.IntegerField(default=60)
    outsideDhakaRate = models.IntegerField(default=130)
    lastSyncTime = models.CharField(max_length=100, default='Just now')
    pendingCodAmount = models.IntegerField(default=0)
    settledCodAmount = models.IntegerField(default=0)

    def __str__(self) -> str:
        return str(self.name)
