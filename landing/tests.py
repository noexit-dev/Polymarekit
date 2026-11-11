from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import MAX_FUNDS, Market, MarketPosition, ProfileWallet


class AccountTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("thunder", password="Stable-pass-408!")
        self.wallet = ProfileWallet.objects.create(user=self.user)

    def test_signup_creates_wallet_and_logs_in(self):
        response = self.client.post(reverse("signup"), {
            "username": "clover", "password1": "Clover-pass-408!", "password2": "Clover-pass-408!",
        })
        self.assertRedirects(response, reverse("profile"))
        user = get_user_model().objects.get(username="clover")
        self.assertTrue(user.check_password("Clover-pass-408!"))
        self.assertEqual(ProfileWallet.objects.get(user=user).wallet_total, 0)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_signup_and_password_validation(self):
        for username, password in [("thunder", "Stable-pass-408!"), ("new", "123")]:
            response = self.client.post(reverse("signup"), {
                "username": username, "password1": password, "password2": password,
            })
            self.assertTrue(response.context["form"].errors)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_private_pages_and_login_logout(self):
        for name in ("profile", "wallet", "delete_account"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)
        self.client.post(reverse("login"), {"username": "thunder", "password": "Stable-pass-408!"})
        self.assertEqual(self.client.get(reverse("wallet")).status_code, 200)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_persists_and_rejects_duplicate_username(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile"), {
            "username": "hoof", "status": "Trotting", "description": "Hay enthusiast",
        })
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(self.user.username, "hoof")
        self.assertEqual(self.wallet.status, "Trotting")
        self.assertEqual(self.wallet.description, "Hay enthusiast")
        get_user_model().objects.create_user("taken")
        response = self.client.post(reverse("profile"), {"username": "taken"})
        self.assertIn("username", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "hoof")

    def test_wallet_additions_validation_and_isolation(self):
        other = get_user_model().objects.create_user("other")
        other_wallet = ProfileWallet.objects.create(user=other)
        self.client.force_login(self.user)
        for currency in ("carrots", "apples", "horseshoes", "hay", "carrots"):
            self.assertRedirects(self.client.post(reverse("wallet"), {
                "currency": currency, "amount": 10, "user": other.pk,
            }), reverse("wallet"))
        for currency, amount in [("carrots", -1), ("carrots", 0), ("carrots", "1.5"),
                                 ("gold", 1), ("hay", MAX_FUNDS), ("hay", MAX_FUNDS + 1)]:
            response = self.client.post(reverse("wallet"), {"currency": currency, "amount": amount})
            self.assertTrue(response.context["form"].errors)
        self.wallet.refresh_from_db()
        other_wallet.refresh_from_db()
        self.assertEqual(self.wallet.carrots, 20)
        self.assertEqual(self.wallet.wallet_total, 50)
        self.assertEqual(other_wallet.wallet_total, 0)
        response = self.client.get(reverse("wallet"))
        self.assertEqual(response.context["wallet"].wallet_total, 50)

    def test_delete_requires_own_password_and_cascades(self):
        other = get_user_model().objects.create_user("other", password="Other-pass-408!")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("delete_account")).status_code, 200)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
        response = self.client.post(reverse("delete_account"), {"password": "Other-pass-408!"})
        self.assertTrue(response.context["form"].errors)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertRedirects(self.client.post(reverse("delete_account"), {
            "password": "Stable-pass-408!",
        }), reverse("home"))
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertFalse(ProfileWallet.objects.filter(pk=self.wallet.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=other.pk).exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for name in ("signup", "profile", "wallet", "delete_account", "logout"):
            self.assertEqual(client.post(reverse(name), {}).status_code, 403)

    def test_markets_are_generated_and_trade_actions_use_wallet(self):
        response = self.client.get(reverse("markets"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Market.objects.count(), 7)
        market = Market.objects.first()
        self.assertGreaterEqual(market.current_value, 20)
        self.assertIn(market.trend_direction, ("up", "down"))
        detail_url = reverse("market_detail", kwargs={"slug": market.slug})
        self.assertContains(self.client.get(detail_url), "Sign in")

        self.client.force_login(self.user)
        self.wallet.carrots = 20
        self.wallet.save(update_fields=["carrots"])
        self.assertEqual(self.client.get(detail_url).status_code, 200)
        self.assertRedirects(self.client.post(detail_url, {
            "currency": "carrots", "amount": 10, "action": "buy",
        }), detail_url)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.carrots, 10)

        response = self.client.post(detail_url, {
            "currency": "carrots", "amount": 11, "action": "buy",
        })
        self.assertContains(response, "You only have 10 carrots.")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.carrots, 10)

        self.assertRedirects(self.client.post(detail_url, {
            "currency": "carrots", "amount": 5, "action": "sell",
        }), detail_url)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.carrots, 15)

    def test_expired_winning_market_pays_double_and_clears_position(self):
        self.client.force_login(self.user)
        self.wallet.carrots = 20
        self.wallet.save(update_fields=["carrots"])
        market = Market.objects.create(
            name="Test market", slug="test-market", category="Racing",
            current_value=80, trend_percent=5, trend_direction="up",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        detail_url = reverse("market_detail", kwargs={"slug": market.slug})
        self.client.post(detail_url, {"currency": "carrots", "amount": 10, "action": "buy"})
        market.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        market.save(update_fields=["expires_at"])
        self.client.get(detail_url)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.carrots, 30)
        self.assertFalse(MarketPosition.objects.filter(user=self.user, market=market).exists())


@override_settings(ALLOWED_HOSTS=["market.example"])
class DeploymentCsrfTests(TestCase):
    def test_public_origin_with_forwarded_host(self):
        for scheme in ("http", "https"):
            with self.subTest(scheme=scheme):
                client = Client(enforce_csrf_checks=True)
                headers = {"HTTP_HOST": "market.example", "HTTP_X_FORWARDED_PROTO": scheme}
                response = client.get(reverse("login"), **headers)
                self.assertEqual(response.status_code, 200)
                token = client.cookies["csrftoken"].value
                data = {"username": "missing", "password": "wrong", "csrfmiddlewaretoken": token}
                response = client.post(reverse("login"), data,
                                       HTTP_ORIGIN=f"{scheme}://market.example", **headers)
                self.assertEqual(response.status_code, 200)
                response = client.post(reverse("login"), data,
                                       HTTP_ORIGIN="https://untrusted.example", **headers)
                self.assertEqual(response.status_code, 403)


class InvestmentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("investor")
        self.wallet = ProfileWallet.objects.create(user=self.user, carrots=100, apples=20)
        self.market = Market.objects.create(
            name="Portfolio market", slug="portfolio-market", category="Racing",
            current_value=80, trend_percent=5, trend_direction="up",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        self.url = self.market.get_absolute_url()
        self.client.force_login(self.user)

    def trade(self, action, amount, currency="carrots"):
        return self.client.post(self.url, {"action": action, "amount": amount, "currency": currency})

    def test_history_and_grouped_holdings(self):
        from .models import Investment
        from decimal import Decimal

        for action, amount, currency in [("buy", 20, "carrots"), ("buy", 10, "carrots"),
                                         ("buy", 5, "apples"), ("sell", 7, "carrots")]:
            self.assertEqual(self.trade(action, amount, currency).status_code, 302)
        trades = list(Investment.objects.all())
        self.assertEqual([(t.transaction_type, t.amount) for t in trades],
                         [("sell", 7), ("buy", 5), ("buy", 10), ("buy", 20)])
        self.assertTrue(all(t.profile == self.wallet and t.market == self.market for t in trades))
        response = self.client.get(reverse("portfolio"))
        self.assertEqual([(p.currency, p.amount) for p in response.context["positions"]],
                         [("apples", 5), ("carrots", 23)])
        self.assertEqual(response.context["positions"][1].estimated_value, Decimal("36.8"))
        self.assertIn(("Carrots", 23), response.context["totals"])
        self.assertContains(response, "36.80")
        self.assertContains(self.client.get(reverse("trade_history")), "Sell")
        self.trade("sell", 23)
        self.assertFalse(MarketPosition.objects.filter(user=self.user, currency="carrots").exists())
        self.assertEqual(Investment.objects.count(), 5)

    def test_rejected_trades_do_not_change_records(self):
        from .models import Investment

        for action, amount, currency in [("buy", 101, "carrots"), ("sell", 1, "carrots"),
                                         ("buy", 0, "carrots"), ("buy", 1, "gold"),
                                         ("invalid", 1, "carrots")]:
            self.assertEqual(self.trade(action, amount, currency).status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.carrots, 100)
        self.assertFalse(Investment.objects.exists())
        self.assertFalse(MarketPosition.objects.exists())

    def test_record_failure_rolls_back_trade(self):
        from unittest.mock import patch

        with patch("landing.views.Investment.objects.create", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                self.trade("buy", 10)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.carrots, 100)
        self.assertFalse(MarketPosition.objects.exists())

    def test_pages_are_private_and_empty_for_other_accounts(self):
        self.trade("buy", 10)
        other = get_user_model().objects.create_user("other-investor")
        self.client.force_login(other)
        self.assertContains(self.client.get(reverse("portfolio")), "You have no open holdings")
        self.assertContains(self.client.get(reverse("trade_history")), "You have no recorded trades")
        self.client.logout()
        for name in ("portfolio", "trade_history"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_settlement_preserves_history_and_account_deletion_removes_it(self):
        from .models import Investment

        self.trade("buy", 10)
        self.market.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        self.market.save(update_fields=["expires_at"])
        self.assertContains(self.client.get(reverse("portfolio")), "You have no open holdings")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.carrots, 110)
        self.assertEqual(Investment.objects.count(), 1)
        self.assertContains(self.client.get(reverse("trade_history")), "Portfolio market")
        self.user.delete()
        self.assertFalse(Investment.objects.exists())
