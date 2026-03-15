from django import forms
from .models import TycoInput, TycoBInput, SycoInput, SycoBInput, FycoInput, FycoBInput


class TycoInputForm(forms.ModelForm):
    class Meta:
        model = TycoInput
        fields = ["subject_name", "teacher_name", "theory_credits", "practical_credits"]


class TycoBInputForm(forms.ModelForm):
    class Meta:
        model = TycoBInput
        fields = ["subject_name", "teacher_name", "theory_credits", "practical_credits"]


class SycoInputForm(forms.ModelForm):
    class Meta:
        model = SycoInput
        fields = ["subject_name", "teacher_name", "theory_credits", "practical_credits"]


class SycoBInputForm(forms.ModelForm):
    class Meta:
        model = SycoBInput
        fields = ["subject_name", "teacher_name", "theory_credits", "practical_credits"]


class FycoInputForm(forms.ModelForm):
    class Meta:
        model = FycoInput
        fields = ["subject_name", "teacher_name", "theory_credits", "practical_credits"]


class FycoBInputForm(forms.ModelForm):
    class Meta:
        model = FycoBInput
        fields = ["subject_name", "teacher_name", "theory_credits", "practical_credits"]
