from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import generate_timetable_view, view_timetable, add_extra_lectures_view

urlpatterns = [
    path(
        "generate/<int:class_id>/", generate_timetable_view, name="generate_timetable"
    ),
    path("view/<int:class_id>/", view_timetable, name="view_timetable"),
    path(
        "add-extra/<int:class_id>/", add_extra_lectures_view, name="add_extra_lectures"
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
