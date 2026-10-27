from django import forms
from django.contrib.auth import get_user_model

from .models import CURRENCIES, MAX_FUNDS, ProfileWallet


class ProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, validators=get_user_model()._meta.get_field("username").validators)

    class Meta:
        model = ProfileWallet
        fields = ("username", "status", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username=username).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


class WalletForm(forms.Form):
    currency = forms.ChoiceField(choices=[(name, name.capitalize()) for name in CURRENCIES])
    amount = forms.IntegerField(min_value=1, max_value=MAX_FUNDS)


class DeleteAccountForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label="Confirm your password")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password
