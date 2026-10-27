from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import MAX_FUNDS, ProfileWallet


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
