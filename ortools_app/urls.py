from django.urls import path
from .views import timetable_input

app_name = "ortools_app"

urlpatterns = [
    path("timetable-input/", timetable_input, name="timetable-input"),
]
