import logging

from django.conf import settings
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
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

logger = logging.getLogger('django')


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
		name = serializer.validated_data.get('name', obj.name)
		new_slug = slugify(name)
		if new_slug != obj.slug:
			elements = Element.objects.filter(platform=obj)
			for element in elements:
				old_set_name = f"{obj.slug}/{element.slug}"
				new_set_name = f"{new_slug}/{element.slug}"
				callback_func = update_set_name(new_set_name)
				aerospike_db.query(settings.AEROSPIKE_NS, old_set_name).foreach(callback_func)
				aerospike_db.truncate(settings.AEROSPIKE_NS, old_set_name, 0)

		if serializer.validated_data.get('name') != obj.name:
			serializer.save(slug=new_slug)

	def perform_destroy(self, instance):
		elements = Element.objects.filter(platform=instance)
		for element in elements:
			set_name = f"{instance.slug}/{element.slug}"
			aerospike_db.truncate(settings.AEROSPIKE_NS, set_name, 0)
		instance.delete()


class ElementListCreateApiView(ListCreateAPIView):
	serializer_class = ElementSerializer

	def get_queryset(self):
		return Element.objects.filter(platform__slug=self.kwargs['platform'])

	def perform_create(self, serializer):
		slug = slugify(serializer.validated_data['name'])
		try:
			platform = Platform.objects.get(slug=self.kwargs['platform'])
		except Platform.DoesNotExist:
			raise ValidationError({"platform": "Does not exist"})
		serializer.save(platform=platform, slug=slug)


class ElementDetailApiView(RetrieveUpdateDestroyAPIView):
	serializer_class = ElementSerializer
	lookup_url_kwarg = 'element'
	lookup_field = 'slug'

	def get_queryset(self):
		return Element.objects.filter(platform__slug=self.kwargs['platform'])

	def perform_update(self, serializer):
		obj = self.get_object()
		name = serializer.validated_data.get('name', obj.name)
		new_slug = slugify(name)
		if new_slug != obj.slug:
			old_set_name = f"{self.kwargs['platform']}/{obj.slug}"
			new_set_name = f"{self.kwargs['platform']}/{new_slug}"
			callback_func = update_set_name(new_set_name)
			aerospike_db.query(settings.AEROSPIKE_NS, old_set_name).foreach(callback_func)
			aerospike_db.truncate(settings.AEROSPIKE_NS, old_set_name, 0)

		if serializer.validated_data.get('name') != obj.name:
			serializer.save(slug=new_slug)

	def perform_destroy(self, instance):
		set_name = f"{instance.platform.slug}/{instance.slug}"
		aerospike_db.truncate(settings.AEROSPIKE_NS, set_name, 0)
		instance.delete()


class RecordListCreateApiView(APIView):
	def get(self, request, **kwargs):
		set_name = f"{kwargs['platform']}/{kwargs['element']}"
		results = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
		results = sorted(convert_results(results), key=lambda e: e['id'])
		return Response(results, status=status.HTTP_200_OK)

	def post(self, request, **kwargs):
		try:
			record_id = int(request.data['value'])
		except (KeyError, ValueError):
			return Response({'value': 'must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			element = Element.objects.get(
				platform__slug=self.kwargs['platform'], slug=self.kwargs['element'])
		except Element.DoesNotExist:
			return Response({"element": "Does not exist"}, status=status.HTTP_400_BAD_REQUEST)

		key = (settings.AEROSPIKE_NS, f"{kwargs['platform']}/{kwargs['element']}", record_id)
		_, meta = aerospike_db.exists(key)
		if meta is not None:
			message = {'value': 'record with this value already exists'}
			return Response(message, status=HTTP_442_ALREADY_EXIST)

		counters = Counter.objects.filter(element=element)
		bins = {str(counter.id): 0 for counter in counters}
		bins['id'] = record_id
		response = collections.OrderedDict(id=record_id)
		for counter in counters:
			response[counter.slug] = f"0/{counter.max_value}"
		aerospike_db.put(key, bins)
		return Response(response, status=status.HTTP_201_CREATED)


class CounterListCreateApiView(ListCreateAPIView):
	serializer_class = CounterSerializer

	def get_queryset(self):
		return Counter.objects.filter(
			element__platform__slug=self.kwargs['platform'], element__slug=self.kwargs['element']
		)

	def perform_create(self, serializer):
		slug = slugify(serializer.validated_data['name'])
		try:
			element = Element.objects.get(
				platform__slug=self.kwargs['platform'], slug=self.kwargs['element'])
		except Element.DoesNotExist:
			raise ValidationError({"element": "Does not exist"})
		serializer.save(element=element, slug=slug)

		callback_func = add_counter_to_record(serializer.data['id'])
		set_name = f"{self.kwargs['platform']}/{self.kwargs['element']}"
		aerospike_db.query(settings.AEROSPIKE_NS, set_name).foreach(callback_func)


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
		query = aerospike_db.query(settings.AEROSPIKE_NS, set_name)
		callback_func = delete_counter_from_record(instance.id)
		query.foreach(callback_func)
		instance.delete()


class CounterActionsApiView(APIView):
	def get_record_key(self):
		set_name = f"{self.kwargs['platform']}/{self.kwargs['element']}"
		return settings.AEROSPIKE_NS, set_name, self.kwargs['uid']

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
