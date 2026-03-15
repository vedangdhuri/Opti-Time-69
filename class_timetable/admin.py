from django.contrib import admin
from .models import MasterSubject


@admin.register(MasterSubject)
class MasterSubjectAdmin(admin.ModelAdmin):
    list_display = (
        "class_name",
        "subject_name",
        "abbreviation",
        "teacher_name",
        "theory_credits",
        "practical_credits",
    )
    list_filter = ("class_name",)
    search_fields = ("subject_name", "teacher_name")
