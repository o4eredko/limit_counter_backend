from django.urls import path, include
from rest_framework.routers import SimpleRouter

from services.views import *

router = SimpleRouter()
router.register('platforms', PlatformViewSet)
router.register('elements', ElementViewSet)

urlpatterns = [
	path('', api_root),
	path('', include(router.urls))

	# path('counters/', CounterListCreateView.as_view(), name='counter-list'),
	# path('<platform>/<element>/<int:uid>/<counter>/', CounterView.as_view(), name='counter-create')
]
