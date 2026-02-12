from django import forms
from .models import TycoAInput, TycoBInput, SycoAInput, SycoBInput

class TycoAInputForm(forms.ModelForm):
    class Meta:
        model = TycoAInput
        fields = ['subject_name', 'teacher_name', 'theory_credits', 'practical_credits']

class TycoBInputForm(forms.ModelForm):
    class Meta:
        model = TycoBInput
        fields = ['subject_name', 'teacher_name', 'theory_credits', 'practical_credits']

class SycoAInputForm(forms.ModelForm):
    class Meta:
        model = SycoAInput
        fields = ['subject_name', 'teacher_name', 'theory_credits', 'practical_credits']

class SycoBInputForm(forms.ModelForm):
    class Meta:
        model = SycoBInput
        fields = ['subject_name', 'teacher_name', 'theory_credits', 'practical_credits']
