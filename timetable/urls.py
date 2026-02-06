# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from django.urls import path
from .views import *

urlpatterns = [
    path("generate/<int:class_id>/", generate_timetable_view, name="generate_timetable"),
    path("view/<int:class_id>/", view_timetable, name="view_timetable"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

