from django.conf import settings
from django.db import models


CURRENCIES = ("carrots", "apples", "horseshoes", "hay")
MAX_FUNDS = 2**63 - 1


class ProfileWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.TextField(max_length=2000, blank=True)
    status = models.CharField(max_length=100, blank=True)
    carrots = models.PositiveBigIntegerField(default=0)
    apples = models.PositiveBigIntegerField(default=0)
    horseshoes = models.PositiveBigIntegerField(default=0)
    hay = models.PositiveBigIntegerField(default=0)

    class Meta:
        db_table = "profile_wallet"

    @property
    def wallet_total(self):
        return sum(getattr(self, currency) for currency in CURRENCIES)
