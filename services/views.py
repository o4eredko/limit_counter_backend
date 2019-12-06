from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from services.models import Platform, Element
from services.serializers import PlatformListCreateSerializer, PlatformDetailSerializer
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
# lookup_field = 'name'


class PlatformDetailApiView(RetrieveUpdateDestroyAPIView):
	queryset = Platform.objects.all()
	serializer_class = PlatformDetailSerializer
	lookup_field = 'name'

# class ElementViewSet(ModelViewSet):
# 	queryset = Element.objects.all()
# 	serializer_class = ElementSerializer

# class ElementCreateApiView(ApiView):
# 	queryset = Element.objects.all()
# 	serializer_class = ElementSerializer

# class CounterListCreateView(ListCreateAPIView):
# 	queryset = Counter.objects.all()
# 	serializer_class = CounterSerializer
#
#
# class CounterView(APIView):
# 	def get(self, request, **kwargs):
# 		print(kwargs)
# 		return Response({'success': True})
