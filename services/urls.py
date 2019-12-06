from django.urls import path, include

from services.views import *

# router.register('elements', ElementViewSet)

urlpatterns = [
	path('', api_root),
	path('platforms/', PlatformListCreateApiView.as_view(), name='platform-list'),
	path('<slug:platform>/', PlatformDetailApiView.as_view(), name='platform-detail'),
	path('<slug:platform>/elements/', ElementListCreateApiView.as_view(), name='element-list'),
	path('<slug:platform>/<slug:element>/', ElementDetailApiView.as_view(), name='element-detail')

	# path('counters/', CounterListCreateView.as_view(), name='counter-list'),
	# path('<platform>/<element>/<int:uid>/<counter>/', CounterView.as_view(), name='counter-create')
]
