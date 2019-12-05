from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.generics import ListCreateAPIView

from services.models import Platform, Element, Counter
from services.serializers import PlatformSerializer, ElementSerializer, CounterSerializer


#
# class PlatformViewSet(ViewSet):
# 	queryset = Platform.objects.all()
# 	serializer_class = PlatformSerializer

class PlatformListCreateView(ListCreateAPIView):
	queryset = Platform.objects.all()
	serializer_class = PlatformSerializer


class ElementListCreateView(ListCreateAPIView):
	queryset = Element.objects.all()
	serializer_class = ElementSerializer


class CounterListCreateView(ListCreateAPIView):
	queryset = Counter.objects.all()
	serializer_class = CounterSerializer
