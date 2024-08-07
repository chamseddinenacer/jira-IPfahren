# report/models.py
from django.db import models

class TestCase(models.Model):
    name = models.CharField(max_length=255)
    verdict = models.CharField(max_length=50)
    domain_expert = models.CharField(max_length=255)
    artifactory_upload_paths = models.TextField()
    used_tbc = models.CharField(max_length=255)
    report_id = models.CharField(max_length=255)
    hw_sample = models.CharField(max_length=255)
