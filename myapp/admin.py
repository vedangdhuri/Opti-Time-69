from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from .models import *


# Custom User admin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("name", "email", "contact", "age", "gender", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "gender")
    search_fields = ("email", "name", "contact")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name", "username", "contact", "age", "gender")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "name", "contact", "age", "gender", "password1", "password2", "is_active", "is_staff")
        }),
    )



# Message admin
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "timestamp", "is_group_message")
    search_fields = ("sender__name", "receiver__name", "text")
    ordering = ("-timestamp",)


# Feedback admin
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "created_at", "resolved")
    search_fields = ("user__name", "message")
    list_filter = ("resolved",)
    ordering = ("-created_at",)


# Remove the Groups menu completely
admin.site.unregister(Group)

# Admin site settings
admin.site.site_header = "Time Table Generator Admin"
admin.site.site_title = "Time Table Generator  Admin Portal"
admin.site.index_title = "Welcome to the Time Table Generator Dashboard"
