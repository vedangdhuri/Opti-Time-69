from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Feedback


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
        fields = ("username", "email", "name", "contact", "age", "gender")

        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email address"}),
            "name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "contact": forms.TextInput(attrs={"placeholder": "Contact number"}),
            "age": forms.NumberInput(attrs={"placeholder": "Age", "min": 18}),
            "gender": forms.Select(),
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
        fields = ["name", "email", "contact", "age", "gender"]

        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email address"}),
            "contact": forms.TextInput(attrs={"placeholder": "Contact number"}),
            "age": forms.NumberInput(attrs={"placeholder": "Age", "min": 18}),
            "gender": forms.Select(),
        }


# ==================================================
# 🔹 FEEDBACK FORM (UI-ENHANCED)
# ==================================================
class FeedbackForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Feedback
        fields = ["message"]

        widgets = {
            "message": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Write your feedback here...",
                "class": "shadow-sm rounded-3",
                "style": "resize:none; background-color:#ffffff;"
            }),
        }

        labels = {
            "message": "Your Feedback",
        }
