from django.db import models

class Person(models.Model):
    email = models.EmailField(unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15, unique=True)
    