from django.urls import path
from . import views

app_name = 'class_timetable'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('input/<str:class_key>/', views.input_data, name='input_data'),
    path('input/<str:class_key>/delete/<int:input_id>/', views.delete_input, name='delete_input'),
    path('generate/<str:class_key>/', views.generate_timetable_view, name='generate'),
    path('view/<str:class_key>/', views.view_timetable, name='view_timetable'),
    path('analytics/<str:class_key>/', views.analytics_view, name='analytics'),
    path('delete/<str:class_key>/', views.delete_timetable, name='delete_timetable'),
]
