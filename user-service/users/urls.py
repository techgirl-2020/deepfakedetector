from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.my_profile, name='my-profile'),
    path('history/', views.detection_history, name='detection-history'),
    path('history/<int:pk>/', views.detection_detail, name='detection-detail'),
    path('detect/', views.detect_image, name='detect-image'),
]