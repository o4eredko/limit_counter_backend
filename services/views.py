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
		elements = Element.objects.filter(platform=instance)
		for element in elements:
			set_name = f"{instance.slug}/{element.slug}"
			aerospike_db.truncate(settings.AEROSPIKE_NAMESPACE, set_name, 0)
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
		set_name = f"{instance.platform.slug}/{instance.slug}"
		aerospike_db.truncate(settings.AEROSPIKE_NAMESPACE, set_name, 0)
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

		key = (settings.AEROSPIKE_NAMESPACE, f"{kwargs['platform']}/{kwargs['element']}", record_id)
		_, meta = aerospike_db.exists(key)
		if meta is not None:
			message = {'value': 'record with this value already exists'}
			return Response(message, status=HTTP_442_ALREADY_EXIST)

		counters = Counter.objects.filter(
			element__platform__slug=kwargs['platform'], element__slug=kwargs['element'])
		bins = {str(counter.id): 0 for counter in counters}
		response = {counter.slug: f"0/{counter.max_value}" for counter in counters}
		response['id'] = bins['id'] = record_id
		aerospike_db.put(key, bins)
		return Response(response, status=status.HTTP_201_CREATED)


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
	def get_record_key(self):
		set_name = f"{self.kwargs['platform']}/{self.kwargs['element']}"
		return settings.AEROSPIKE_NAMESPACE, set_name, self.kwargs['uid']

	def get_counter_with_value(self, key):
		counter = Counter.objects.get(
			element__platform__slug=self.kwargs['platform'],
			element__slug=self.kwargs['element'],
			slug=self.kwargs['counter']
		)
		_, _, bins = aerospike_db.get(key)
		return counter, bins[str(counter.id)]

	def get(self, request, **kwargs):
		key = self.get_record_key()
		try:
			_, counter_value = self.get_counter_with_value(key)
		except (exception.AerospikeError, Counter.DoesNotExist):
			return Response(status=HTTP_441_NOT_EXIST)
		return Response(counter_value, status=status.HTTP_200_OK)

	def post(self, request, **kwargs):
		try:
			value = int(request.data['value'])
			if value < 0:
				raise ValueError()
		except (KeyError, ValueError):
			message = {'value': 'must be a positive integer'}
			return Response(message, status=status.HTTP_400_BAD_REQUEST)

		key = self.get_record_key()
		try:
			counter, counter_value = self.get_counter_with_value(key)
		except (exception.AerospikeError, Counter.DoesNotExist):
			return Response(status=HTTP_441_NOT_EXIST)

		if counter_value + value > counter.max_value:
			return Response(status=HTTP_440_FULL)
		aerospike_db.increment(key, str(counter.id), value)
		return Response(counter_value + value, status=status.HTTP_200_OK)
