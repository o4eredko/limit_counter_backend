from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from limit_counter import settings
from services.models import Platform, Element
from services.serializers import (
	PlatformListCreateSerializer,
	PlatformDetailSerializer,
	ElementListCreateSerializer,
	ElementDetailSerializer,
)
from services import client

HTTP_441_NOT_EXIST = 441
HTTP_442_ALREADY_EXIST = 442


@api_view(['GET'])
def api_root(request, format=None):
	return Response({
		'platforms': reverse('platform-list', request=request, format=format),
		# 'elements': reverse('element-list', request=request, format=format),
		# 'counters': reverse('counter-list', request=request, format=format),
	})


class PlatformListCreateApiView(ListCreateAPIView):
	queryset = Platform.objects.all()
	serializer_class = PlatformListCreateSerializer


class PlatformDetailApiView(RetrieveUpdateDestroyAPIView):
	queryset = Platform.objects.all()
	serializer_class = PlatformDetailSerializer
	lookup_url_kwarg = 'platform'
	lookup_field = 'name'


class ElementListCreateApiView(ListCreateAPIView):
	serializer_class = ElementListCreateSerializer

	def get_queryset(self):
		platform_name = self.kwargs['platform']
		return Element.objects.filter(platform=Platform.objects.get(name=platform_name))

	def perform_create(self, serializer):
		platform_name = self.kwargs['platform']
		serializer.save(platform=Platform.objects.get(name=platform_name))


class ElementDetailApiView(RetrieveUpdateDestroyAPIView):
	queryset = Element.objects.all()
	serializer_class = ElementDetailSerializer
	lookup_url_kwarg = 'element'
	lookup_field = 'name'

	def post(self, request, *args, **kwargs):
		record_set = f"{kwargs['platform']}/{kwargs['element']}"
		record_key = int(request.data['index'])
		key = (settings.AEROSPIKE_NAMESPACE, record_set, record_key)

		_, meta = client.exists(key)
		if meta is not None:
			return Response(status=HTTP_442_ALREADY_EXIST)

		client.put(key, {'a': 1})
		return Response(status=status.HTTP_201_CREATED)
# serializer = self.get_serializer(data=request.data)
# serializer.is_valid(raise_exception=True)
# self.perform_create(serializer)
# headers = self.get_success_headers(serializer.data)
# return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
