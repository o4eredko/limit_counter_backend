from pprint import pprint
from django.conf import settings
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from aerospike import exception

from services.aerospike_utils import *
from services.models import Platform, Element, Counter
from services.serializers import (PlatformSerializer, ElementSerializer, CounterSerializer)

HTTP_440_FULL = 440
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
		obj = self.get_object()
		slug = slugify(serializer.validated_data.get('name', obj.slug))
		serializer.save(slug=slug)
		query = aerospike_db.query(settings.AEROSPIKE_NAMESPACE)
		callback_func = update_set_name(obj.slug, slug)
		query.foreach(callback_func)

	def perform_destroy(self, instance):
		query = aerospike_db.query(settings.AEROSPIKE_NAMESPACE)
		callback_func = delete_set(platform=instance.slug)
		query.foreach(callback_func)
		instance.delete()


class ElementListCreateApiView(ListCreateAPIView):
	serializer_class = ElementSerializer

	def get_queryset(self):
		return Element.objects.filter(platform__slug=self.kwargs['platform'])

	def perform_create(self, serializer):
		platform_slug = self.kwargs['platform']
		slug = slugify(serializer.validated_data['name'])
		platform = Platform.objects.filter(slug=platform_slug).first()
		serializer.save(platform=platform, slug=slug)


class ElementDetailApiView(RetrieveUpdateDestroyAPIView):
	serializer_class = ElementSerializer
	lookup_url_kwarg = 'element'
	lookup_field = 'slug'

	def get_queryset(self):
		return Element.objects.filter(platform__slug=self.kwargs['platform'])

	def perform_update(self, serializer):
		obj = self.get_object()
		slug = slugify(serializer.validated_data.get('name', obj.slug))
		serializer.save(slug=slug)
		query = aerospike_db.query(settings.AEROSPIKE_NAMESPACE)
		callback_func = update_set_name(obj.slug, slug)
		query.foreach(callback_func)

	def perform_destroy(self, instance):
		query = aerospike_db.query(settings.AEROSPIKE_NAMESPACE)
		callback_func = delete_set(element=instance.slug)
		query.foreach(callback_func)
		instance.delete()


class RecordListCreateApiView(APIView):
	def get(self, request, **kwargs):
		set_name = f"{kwargs['platform']}/{kwargs['element']}"
		results = aerospike_db.scan(settings.AEROSPIKE_NAMESPACE, set_name).results()
		return Response(convert_results(results), status=status.HTTP_200_OK)

	def post(self, request, **kwargs):
		try:
			record_id = int(request.data['value'])
		except (KeyError, ValueError):
			return Response({'value': 'must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

		element_slug = self.kwargs['element']
		platform_slug = self.kwargs['platform']
		key = (settings.AEROSPIKE_NAMESPACE, f"{platform_slug}/{element_slug}", record_id)
		_, meta = aerospike_db.exists(key)
		if meta is not None:
			message = {'value': 'record with this value already exists'}
			return Response(message, status=HTTP_442_ALREADY_EXIST)

		counters = Counter.objects.filter(element__platform__slug=platform_slug,
										  element__slug=element_slug)
		bins = {str(counter.id): 0 for counter in counters}
		bins['key'] = record_id
		aerospike_db.put(key, bins)
		return Response(status=status.HTTP_201_CREATED)


@api_view(['GET'])
def record_list(request, **kwargs):
	element_slug = kwargs['element']
	platform_slug = kwargs['platform']
	scan = aerospike_db.query(settings.AEROSPIKE_NAMESPACE, f"{platform_slug}/{element_slug}")
	pprint(scan.results())
	return Response([], status=status.HTTP_200_OK)


class CounterListCreateApiView(ListCreateAPIView):
	serializer_class = CounterSerializer

	def get_queryset(self):
		return Counter.objects.filter(element__platform__slug=self.kwargs['platform'],
									  element__slug=self.kwargs['element'])

	def perform_create(self, serializer):
		slug = slugify(serializer.validated_data['name'])
		element_slug = self.kwargs['element']
		platform_slug = self.kwargs['platform']
		element = Element.objects.filter(platform__slug=platform_slug,
										 slug=element_slug).first()
		serializer.save(element=element, slug=slug)

		query = aerospike_db.query(settings.AEROSPIKE_NAMESPACE,
								   f"{platform_slug}/{element_slug}")
		callback_func = add_counter_to_record(serializer.data['id'])
		query.foreach(callback_func)


class CounterDetailApiView(RetrieveUpdateDestroyAPIView):
	serializer_class = CounterSerializer
	lookup_url_kwarg = 'counter'
	lookup_field = 'slug'

	def get_queryset(self):
		return Counter.objects.filter(element__platform__slug=self.kwargs['platform'],
									  element__slug=self.kwargs['element'])

	def perform_update(self, serializer):
		obj = self.get_object()
		slug = slugify(serializer.validated_data.get('name', obj.slug))
		serializer.save(slug=slug)

	def perform_destroy(self, instance):
		set_name = f"{self.kwargs['platform']}/{self.kwargs['element']}"
		query = aerospike_db.query(settings.AEROSPIKE_NAMESPACE, set_name)
		callback_func = delete_counter(instance.id)
		query.foreach(callback_func)
		instance.delete()


class CounterActionsApiView(APIView):
	def get(self, request, *args, **kwargs):
		element_slug = kwargs['element']
		platform_slug = kwargs['platform']
		key = (settings.AEROSPIKE_NAMESPACE, f"{platform_slug}/{element_slug}", kwargs['uid'])
		counter = Counter.objects.filter(element__platform__slug=platform_slug,
										 element__slug=element_slug,
										 slug=kwargs['counter']).first()
		try:
			_, _, bins = aerospike_db.get(key)
			result = bins[str(counter.id)]
		except (exception.AerospikeError, AttributeError):
			return Response(status=HTTP_441_NOT_EXIST)
		return Response(result, status=status.HTTP_200_OK)

	def post(self, request, *args, **kwargs):
		try:
			value = int(request.data['value'])
		except (KeyError, ValueError):
			return Response({'value': 'must be an Integer'}, status=status.HTTP_400_BAD_REQUEST)

		element_slug = kwargs['element']
		platform_slug = kwargs['platform']
		key = (settings.AEROSPIKE_NAMESPACE, f"{platform_slug}/{element_slug}", kwargs['uid'])
		counter = Counter.objects.filter(element__slug=element_slug,
										 slug=kwargs['counter']).first()
		try:
			_, _, bins = aerospike_db.get(key)
			counter_value = bins[str(counter.id)]
		except (exception.AerospikeError, KeyError):
			return Response(status=HTTP_441_NOT_EXIST)

		if counter_value + value > counter.max_value:
			return Response(status=HTTP_440_FULL)
		aerospike_db.increment(key, str(counter.id), value)
		return Response(status=status.HTTP_200_OK)
