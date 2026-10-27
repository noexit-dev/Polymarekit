from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import DeleteAccountForm, ProfileForm, WalletForm
from .models import CURRENCIES, MAX_FUNDS, ProfileWallet


def home(request):
    markets = [
        {
            "category": "Weather",
            "color": "sky",
            "question": "Will the first frost arrive before November?",
            "odds": 64,
            "change": "+8.4%",
            "direction": "up",
            "slug": "first-frost",
        },
        {
            "category": "Racing",
            "color": "amber",
            "question": "Will Thunder Hoof win the autumn cup?",
            "odds": 42,
            "change": "-3.1%",
            "direction": "down",
            "slug": "thunder-hoof",
        },
        {
            "category": "Supplies",
            "color": "emerald",
            "question": "Will hay prices rise this month?",
            "odds": 71,
            "change": "+12.7%",
            "direction": "up",
            "slug": "hay-prices",
        },
    ]
    return render(request, "landing/home.html", {"markets": markets})


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
