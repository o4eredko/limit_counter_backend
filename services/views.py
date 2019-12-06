from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, \
	get_object_or_404

from services.models import Platform, Element
from services.serializers import (
	PlatformListCreateSerializer,
	PlatformDetailSerializer,
	ElementListCreateSerializer
)
from services import client


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
	queryset = Element.objects.all()
	serializer_class = ElementListCreateSerializer
	lookup_field = 'element'

	def perform_create(self, serializer):
		platform_name = self.kwargs.get('name')
		platform = Platform.objects.get(name=platform_name)
		serializer.save(platform=platform)
