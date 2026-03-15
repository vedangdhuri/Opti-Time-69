from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


# ==================================================
# 🔹 BOOTSTRAP FORM MIXIN (SMART & SAFE)
# ==================================================
class BootstrapFormMixin:
    """
    Automatically adds Bootstrap 5 classes to all fields
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            base_class = widget.attrs.get("class", "")

            if isinstance(widget, forms.Select):
                widget.attrs["class"] = f"{base_class} form-select"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = f"{base_class} form-control"
            else:
                widget.attrs["class"] = f"{base_class} form-control"


# ==================================================
# 🔹 USER REGISTRATION FORM
# ==================================================
class CustomUserCreationForm(BootstrapFormMixin, UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("username", "email", "name")

        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email address"}),
            "name": forms.TextInput(attrs={"placeholder": "Full name"}),
        }

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("Username is already taken.")
        return username


# ==================================================
# 🔹 PROFILE EDIT FORM
# ==================================================
class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["name", "email"]

        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email address"}),
        }
