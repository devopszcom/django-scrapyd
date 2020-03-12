from django.db import models


# Create your models here.
class CrawlerNode(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    host = models.CharField(max_length=255, default="127.0.0.1")
    port = models.CharField(max_length=255, default=6800)

    def __str__(self):
        return "{} - {}".format(self.id, self.name)
