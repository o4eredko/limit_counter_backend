from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from limit_counter import settings
from services.models import Platform, Element
from services.serializers import (
	PlatformSerializer,
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
	})


class PlatformListCreateApiView(ListCreateAPIView):
	queryset = Platform.objects.all()
	serializer_class = PlatformSerializer

	def perform_create(self, serializer):
		serializer.save(slug=slugify(serializer.validated_data['name']))


class PlatformDetailApiView(RetrieveUpdateDestroyAPIView):
	queryset = Platform.objects.all()
	serializer_class = PlatformSerializer
	lookup_url_kwarg = 'platform'
	lookup_field = 'slug'

	def perform_update(self, serializer):
		serializer.save(slug=slugify(serializer.validated_data['name']))


class ElementListCreateApiView(ListCreateAPIView):
	serializer_class = ElementListCreateSerializer

	def get_queryset(self):
		platform = Platform.objects.filter(slug=self.kwargs['platform']).first()
		return Element.objects.filter(platform=platform)

	def perform_create(self, serializer):
		name = serializer.validated_data['name']
		platform_slug = self.kwargs['platform']
		platform = Platform.objects.filter(slug=platform_slug).first()
		serializer.save(platform=platform, slug=slugify(name))


class ElementDetailApiView(RetrieveUpdateDestroyAPIView):
	serializer_class = ElementDetailSerializer
	lookup_url_kwarg = 'element'
	lookup_field = 'slug'

	def get_queryset(self):
		platform = Platform.objects.filter(slug=self.kwargs['platform']).first()
		return Element.objects.filter(platform=platform)

	def perform_update(self, serializer):
		serializer.save(slug=slugify(serializer.validated_data['name']))

	def post(self, request, *args, **kwargs):
		record_set = f"{kwargs['platform']}/{kwargs['element']}"
		record_key = int(request.data['index'])
		key = (settings.AEROSPIKE_NAMESPACE, record_set, record_key)

		_, meta = client.exists(key)
		if meta is not None:
			return Response(status=HTTP_442_ALREADY_EXIST)

		client.put(key, {'a': 1})
		return Response(status=status.HTTP_201_CREATED)

# class CounterListCreateApiView(ListCreateAPIView):
# 	queryset = Counter.objects.all()
# 	serializer_class = CounterListCreateSerializer
