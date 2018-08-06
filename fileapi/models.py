from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class UploadAttempt(models.Model):
    user = models.ForeignKey(User)
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s %s" % (self.user.email, self.created_at,)


class ReportsFiles(models.Model):
    STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    )
    user = models.ForeignKey(User)
    report_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, choices=STATUS, default='completed')

    def __str__(self):
        return "%s %s" % (self.user.email, self.updated_at,)
