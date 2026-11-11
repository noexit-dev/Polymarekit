from django.conf import settings
from decimal import Decimal
from django.db import models
from django.urls import reverse


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


class Market(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.CharField(max_length=80)
    current_value = models.PositiveIntegerField()
    trend_percent = models.DecimalField(max_digits=5, decimal_places=1)
    trend_direction = models.CharField(max_length=4, choices=(("up", "Up"), ("down", "Down")))
    trend_updated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ("name",)

    def get_absolute_url(self):
        return reverse("market_detail", kwargs={"slug": self.slug})


class MarketPosition(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    currency = models.CharField(max_length=20, choices=[(name, name) for name in CURRENCIES])
    amount = models.PositiveBigIntegerField()

    @property
    def estimated_value(self):
        return Decimal(self.amount) * self.market.current_value * 2 / 100

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "market", "currency"), name="unique_market_position"),
        ]


class Investment(models.Model):
    profile = models.ForeignKey(ProfileWallet, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.PROTECT)
    amount = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=20, choices=[(name, name) for name in CURRENCIES])
    transaction_type = models.CharField(max_length=4, choices=(("buy", "Buy"), ("sell", "Sell")))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "investments"
        ordering = ("-created_at", "-pk")
