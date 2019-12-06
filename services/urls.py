from django.urls import path, include

from services.views import *

# router.register('elements', ElementViewSet)

urlpatterns = [
	path('', api_root),
	path('platforms/', PlatformListCreateApiView.as_view(), name='platform-list'),
	path('<slug:name>/', PlatformDetailApiView.as_view(), name='platform-detail'),
	# path('<slug:platform>/')
	# path('<platform>/<element>/', ElementCreateApiView.as_view())

	# path('counters/', CounterListCreateView.as_view(), name='counter-list'),
	# path('<platform>/<element>/<int:uid>/<counter>/', CounterView.as_view(), name='counter-create')
]
