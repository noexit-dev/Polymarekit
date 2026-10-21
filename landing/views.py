from django.http import HttpResponse
from django.shortcuts import render


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
