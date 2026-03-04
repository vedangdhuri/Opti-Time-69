# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Q
from django.conf import settings

from django.contrib.auth import get_user_model

from .forms import CustomUserCreationForm, ProfileForm
from .models import CustomUser


def base(request):
    return render(request, "base.html")


def signup_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")  # Redirect to dashboard after signup
        else:
            # If form is not valid, it will pass validation errors back to the template
            return render(request, "registration/signup.html", {"form": form})
    else:
        form = CustomUserCreationForm()

    # If the form is accessed via GET (for example, on initial page load)
    return render(request, "registration/signup.html", {"form": form})


# Handle user logout
def logout_view(request):
    logout(request)
    return redirect("login")


# profile
@login_required
def profile_view(request):
    return render(request, "account/profile.html", {"user": request.user})


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def edit_profile(request):
    user = request.user  # Get the current logged-in user

    if request.method == "POST":
        form = ProfileForm(
            request.POST, instance=user
        )  # Pre-fill the form with user's current data
        if form.is_valid():
            form.save()  # Save the updated data to the database
            return redirect("profile")  # Redirect to profile page (or dashboard, etc.)
    else:
        form = ProfileForm(instance=user)  # Display the form with user's current data

    return render(request, "account/edit_profile.html", {"form": form})


# dashboard
from django.shortcuts import render
from timetable.models import AcademicClass, Subject, Room, Batch, TimetableEntry, Day
from django.db.models import Count


def dashboard(request):
    context = {
        # Basic counts
        "total_classes": AcademicClass.objects.count(),
        "total_subjects": Subject.objects.count(),
        "total_rooms": Room.objects.count(),
        "total_batches": Batch.objects.count(),
        # Timetable analytics
        "total_entries": TimetableEntry.objects.count(),
        "total_lectures": TimetableEntry.objects.filter(
            is_break=False, batch__isnull=True
        ).count(),
        "total_practicals": TimetableEntry.objects.filter(batch__isnull=False).count(),
        "total_breaks": TimetableEntry.objects.filter(is_break=True).count(),
        # Day-wise load
        "day_wise_load": Day.objects.annotate(total=Count("timetableentry")),
    }

    return render(request, "dashboard/dashboard.html", context)


def about(request):
    return render(request, "about.html")


# views.py
