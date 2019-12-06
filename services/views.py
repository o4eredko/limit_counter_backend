from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView

from services.models import Platform, Element
from services.serializers import (
	PlatformListCreateSerializer,
	PlatformDetailSerializer,
	ElementListCreateSerializer,
	ElementDetailSerializer,
)


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
