from django.urls import path, include

from services.views import *


urlpatterns = [
	path('platforms/', PlatformListCreateView.as_view()),
	path('elements/', ElementListCreateView.as_view()),
	path('counters/', CounterListCreateView.as_view()),
]
