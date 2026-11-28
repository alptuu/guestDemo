from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
)
from django.contrib.auth.password_validation import validate_password

from .models import Profile
from .permissions import get_profile

User = get_user_model()


class StyledFormMixin:
    """Tüm alanlara panel CSS sınıfını ekler."""

    def _style_fields(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check")
            else:
                widget.attrs.setdefault("class", "form-control")


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        self.fields["username"].widget.attrs.update(
            {"placeholder": "Kullanıcı adı", "autofocus": True, "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "Parola", "autocomplete": "current-password"}
        )


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class UserCreateForm(StyledFormMixin, forms.ModelForm):
    role = forms.ChoiceField(label="Rol", choices=Profile.ROLE_CHOICES, initial=Profile.ROLE_PERSONNEL)
    password1 = forms.CharField(label="Parola", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(
        label="Parola (tekrar)", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self._style_fields()

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "Parolalar eşleşmiyor.")
            else:
                candidate = User(
                    username=cleaned.get("username", ""),
                    first_name=cleaned.get("first_name", ""),
                    last_name=cleaned.get("last_name", ""),
                    email=cleaned.get("email", ""),
                )
                try:
                    validate_password(p1, candidate)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.save()
        profile = user.profile
        profile.role = self.cleaned_data["role"]
        profile.save(update_fields=["role"])
        return user


class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    role = forms.ChoiceField(label="Rol", choices=Profile.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active"]
        labels = {"is_active": "Hesap aktif"}

    def __init__(self, *args, editing_self=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["role"].initial = get_profile(self.instance).role
        if editing_self:
            # Yönetici kendi rolünü düşüremez veya hesabını pasifleştiremez.
            for name in ("role", "is_active"):
                self.fields[name].disabled = True
                self.fields[name].help_text = "Kendi hesabınız için değiştirilemez."
        self._style_fields()

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile = user.profile
        profile.role = self.cleaned_data["role"]
        profile.save(update_fields=["role"])
        return user
