from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VIEWSETS, GroupViewSet

router = DefaultRouter()

for model_name, viewset in VIEWSETS.items():
    route_name = model_name.replace(' ', '-').lower()
    router.register(route_name, viewset, basename=route_name)

router.register(r'group', GroupViewSet)

urlpatterns = [
    path('', include(router.urls))
]