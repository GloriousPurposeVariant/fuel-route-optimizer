from django.db import models


class City(models.Model):
    """A US place from the Census Gazetteer, used for offline geocoding."""

    name = models.CharField(max_length=120)
    state = models.CharField(max_length=2)
    key = models.CharField(max_length=120)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key", "state"], name="unique_city_key_per_state"),
        ]

    def __str__(self):
        return f"{self.name}, {self.state}"


class FuelStation(models.Model):
    """One US truck stop, deduplicated to its cheapest price."""

    opis_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=2)
    rack_id = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=8)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state}) ${self.price}"
