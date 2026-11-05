from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.text import slugify

from .forms import DeleteAccountForm, MarketActionForm, ProfileForm, WalletForm
from .models import CURRENCIES, MAX_FUNDS, Market, MarketPosition, ProfileWallet

MARKET_LIFETIME = 60 * 60
TREND_LIFETIME = 60
FIXED_PAYOUT_MULTIPLIER = 2


MARKET_SEEDS = (
    ("Racing", "Will Thunder Hoof win the Autumn Cup?"),
    ("Training", "Will more horses break a speed record this season?"),
    ("Supplies", "Will hay prices rise before winter?"),
    ("Weather", "Will the first frost arrive before November?"),
    ("Pasture", "Will Clover Field open a new pasture this month?"),
    ("Breeding", "Will the next foal season set a local record?"),
    ("Stable life", "Will horses spend more time napping this week?"),
)


def ensure_markets():
    from datetime import timedelta
    from random import randint

    now = timezone.now()

    for category, name in MARKET_SEEDS:
        slug = slugify(name)
        Market.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "category": category,
                "current_value": randint(20, 85),
                "trend_percent": randint(1, 15),
                "trend_direction": "up" if randint(0, 1) else "down",
                "expires_at": now + timedelta(seconds=MARKET_LIFETIME),
            },
        )


def refresh_market(market):
    from datetime import timedelta
    from random import randint

    now = timezone.now()
    if market.expires_at <= now:
        with transaction.atomic():
            market = Market.objects.select_for_update().get(pk=market.pk)
            if market.expires_at <= now:
                winning = market.current_value >= 50
                positions = MarketPosition.objects.filter(market=market).select_related("user")
                for position in positions:
                    if winning:
                        wallet, _ = ProfileWallet.objects.get_or_create(user=position.user)
                        setattr(
                            wallet,
                            position.currency,
                            getattr(wallet, position.currency) + position.amount * FIXED_PAYOUT_MULTIPLIER,
                        )
                        wallet.save(update_fields=[position.currency])
                    position.delete()
                market.current_value = randint(20, 85)
                market.trend_percent = randint(1, 15)
                market.trend_direction = "up" if randint(0, 1) else "down"
                market.trend_updated_at = now
                market.expires_at = now + timedelta(seconds=MARKET_LIFETIME)
                market.save()
    elif market.trend_updated_at + timedelta(seconds=TREND_LIFETIME) <= now:
        market.trend_percent = randint(1, 15)
        market.trend_direction = "up" if randint(0, 1) else "down"
        market.trend_updated_at = now
        market.save(update_fields=["trend_percent", "trend_direction", "trend_updated_at"])
    return market


def current_markets():
    ensure_markets()
    return [refresh_market(market) for market in Market.objects.all()]


def home(request):
    return render(request, "landing/home.html", {"markets": current_markets()[:3]})


def markets(request):
    return render(request, "landing/markets.html", {"markets": current_markets()})


def market_detail(request, slug):
    ensure_markets()
    market = refresh_market(Market.objects.get(slug=slug))
    wallet = form = None
    if request.user.is_authenticated:
        wallet, _ = ProfileWallet.objects.get_or_create(user=request.user)
        form = MarketActionForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form is not None and form.is_valid():
        currency = form.cleaned_data["currency"]
        amount = form.cleaned_data["amount"]
        action = request.POST.get("action")
        balance = getattr(wallet, currency)
        if action == "buy":
            if amount > balance:
                form.add_error("amount", f"You only have {balance} {currency}.")
            else:
                setattr(wallet, currency, balance - amount)
                wallet.save(update_fields=[currency])
                position, _ = MarketPosition.objects.get_or_create(
                    user=request.user, market=market, currency=currency,
                    defaults={"amount": 0},
                )
                position.amount += amount
                position.save(update_fields=["amount"])
                messages.success(request, f"Bought {amount} {currency} of {market.name}.")
                return redirect(market.get_absolute_url())
        elif action == "sell":
            position = MarketPosition.objects.filter(
                user=request.user, market=market, currency=currency,
            ).first()
            if not position or amount > position.amount:
                form.add_error("amount", "You do not have enough of this market position to sell.")
            elif balance > MAX_FUNDS - amount:
                form.add_error("amount", "This sale exceeds the wallet's storage limit.")
            else:
                setattr(wallet, currency, balance + amount)
                wallet.save(update_fields=[currency])
                position.amount -= amount
                position.save(update_fields=["amount"])
                if not position.amount:
                    position.delete()
                messages.success(request, f"Sold {amount} {currency} of {market.name}.")
                return redirect(market.get_absolute_url())
        else:
            form.add_error(None, "Choose whether to buy or sell.")
    return render(request, "landing/market_detail.html", {
        "market": market,
        "form": form,
        "wallet": wallet,
        "balances": (
            [(currency.capitalize(), getattr(wallet, currency)) for currency in CURRENCIES]
            if wallet else []
        ),
    })


def health(request):
    return HttpResponse("ok")


def signup(request):
    if request.user.is_authenticated:
        return redirect("profile")
    form = UserCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            ProfileWallet.objects.create(user=user)
        login(request, user)
        messages.success(request, "Welcome to Polymarekit! Edit your profile and add fake funds to your wallet to get started.")
        return redirect("profile")
    return render(request, "landing/signup.html", {"form": form})


@login_required
def profile(request):
    wallet, _ = ProfileWallet.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST if request.method == "POST" else None, instance=wallet,
                       initial={"username": request.user.username})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
            request.user.username = form.cleaned_data["username"]
            request.user.save(update_fields=["username"])
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "landing/profile.html", {"form": form})


@login_required
def wallet(request):
    account, _ = ProfileWallet.objects.get_or_create(user=request.user)
    form = WalletForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        currency = form.cleaned_data["currency"]
        amount = form.cleaned_data["amount"]
        updated = ProfileWallet.objects.filter(pk=account.pk, **{f"{currency}__lte": MAX_FUNDS - amount}).update(
            **{currency: F(currency) + amount})
        if updated:
            messages.success(request, "Fake funds added to your wallet.")
            return redirect("wallet")
        form.add_error("amount", "This addition exceeds the wallet's storage limit.")
    return render(request, "landing/wallet.html", {
        "form": form, "wallet": account,
        "balances": [(currency.capitalize(), getattr(account, currency)) for currency in CURRENCIES],
    })


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.user, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        request.user.delete()
        logout(request)
        messages.success(request, "Your account and wallet have been deleted.")
        return redirect("home")
    return render(request, "landing/delete_account.html", {"form": form})
