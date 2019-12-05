from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.generics import ListCreateAPIView

from services.models import Platform, Element, Counter
from services.serializers import PlatformSerializer, ElementSerializer, CounterSerializer


@api_view(['GET'])
def api_root(request, format=None):
	return Response({
		'platforms': reverse('platform-list', request=request, format=format),
		'elements': reverse('element-list', request=request, format=format),
		'counters': reverse('counter-list', request=request, format=format),
	})

class PlatformListCreateView(ListCreateAPIView):
	queryset = Platform.objects.all()
	serializer_class = PlatformSerializer


class ElementListCreateView(ListCreateAPIView):
	queryset = Element.objects.all()
	serializer_class = ElementSerializer


class CounterListCreateView(ListCreateAPIView):
	queryset = Counter.objects.all()
	serializer_class = CounterSerializer


class CounterView(APIView):
	def get(self, request, **kwargs):
		print(kwargs)
		return Response({'success': True})
