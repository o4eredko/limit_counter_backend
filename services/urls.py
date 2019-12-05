from django.urls import path, include

from services.views import *


urlpatterns = [
	path('', api_root),
	path('platforms/', PlatformListCreateView.as_view(), name='platform-list'),
	path('elements/', ElementListCreateView.as_view(), name='element-list'),
	path('counters/', CounterListCreateView.as_view(), name='counter-list'),
	path('<platform>/<element>/<int:uid>/<counter>/', CounterView.as_view(), name='counter-create')
]
