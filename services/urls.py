from django.urls import path

from services.views import *

urlpatterns = [
	path('', api_root),

	path('platforms/', PlatformListCreateApiView.as_view(), name='platform-list'),
	path('<slug:platform>/', PlatformDetailApiView.as_view(), name='platform-detail'),

	path('<slug:platform>/elements/', ElementListCreateApiView.as_view(), name='element-list'),
	path('<slug:platform>/<slug:element>/', ElementDetailApiView.as_view(), name='element-detail'),
	path('<slug:platform>/<slug:element>/records/',
		 RecordListCreateApiView.as_view(), name='record-list'),

	path('<slug:platform>/<slug:element>/counters/',
		 CounterListCreateApiView.as_view(), name='counter-list'),
	path('<slug:platform>/<slug:element>/<slug:counter>/',
		 CounterDetailApiView.as_view(), name='counter-detail'),

	path('<slug:platform>/<slug:element>/<int:uid>/<slug:counter>/',
		 CounterActionsApiView.as_view(), name='counter-actions')
]
