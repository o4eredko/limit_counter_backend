from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from aerospike import exception

from limit_counter import settings
from services.models import Platform, Element, Counter
from services.serializers import (PlatformSerializer, ElementSerializer, CounterSerializer)
from services import aerospike

HTTP_440_FULL = 440
HTTP_441_NOT_EXIST = 441
HTTP_442_ALREADY_EXIST = 442


@api_view(['GET'])
def api_root(request, format=None):
	return Response({
		'platforms': reverse('platform-list', request=request, format=format),
	})


def get_add_counter_to_record(slug, max_value):
	def add_counter_to_record(record):
		key, _, _ = record
		bins = {
			slug: 0,
			f"{slug}Max": max_value
		}
		aerospike.put(key, bins)

	return add_counter_to_record


def get_update_counter_max_value(slug, max_value):
	def update_counter_max_value(record):
		key, _, _ = record
		bins = {f"{slug}Max": max_value}
		aerospike.put(key, bins)

	return update_counter_max_value


def get_update_counter_name(old_slug, new_slug):
	def update_counter_name(record):
		key, _, old_bins = record
		aerospike.remove_bin(key, [old_slug, f"{old_slug}Max"])
		bins = {
			new_slug: old_bins[old_slug],
			f"{new_slug}Max": old_bins[f"{old_slug}Max"],
		}
		aerospike.put(key, bins)

	return update_counter_name


def get_delete_counter(slug):
	def delete_counter(record):
		key, _, _ = record
		aerospike.remove_bin(key, [slug, f"{slug}Max"])

	return delete_counter


def get_update_set_name(old_name_part, new_name_part):
	def update_set_name(record):
		key, _, bins = record
		namespace, set_name, *_ = key
		name_parts = set_name.split('/')
		try:
			index = name_parts.index(old_name_part)
		except ValueError:
			return
		else:
			name_parts[index] = new_name_part
			aerospike.put((namespace, '/'.join(name_parts), bins['key']), bins)
			aerospike.remove(key)

	return update_set_name


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
		slug = slugify(serializer.validated_data['name'])
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE)
		query.foreach(get_update_set_name(obj.slug, slug))
		serializer.save(slug=slug)


class ElementListCreateApiView(ListCreateAPIView):
	serializer_class = ElementSerializer

	def get_queryset(self):
		platform = Platform.objects.filter(slug=self.kwargs['platform']).first()
		return Element.objects.filter(platform=platform)

	def perform_create(self, serializer):
		name = serializer.validated_data['name']
		platform_slug = self.kwargs['platform']
		platform = Platform.objects.filter(slug=platform_slug).first()
		serializer.save(platform=platform, slug=slugify(name))


class ElementDetailApiView(RetrieveUpdateDestroyAPIView):
	serializer_class = ElementSerializer
	lookup_url_kwarg = 'element'
	lookup_field = 'slug'

	def get_queryset(self):
		platform = Platform.objects.filter(slug=self.kwargs['platform']).first()
		return Element.objects.filter(platform=platform)

	def perform_update(self, serializer):
		obj = self.get_object()
		slug = slugify(serializer.validated_data['name'])
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE)
		query.foreach(get_update_set_name(obj.slug, slug))
		serializer.save(slug=slug)

	def post(self, request, *args, **kwargs):
		record_set = f"{kwargs['platform']}/{kwargs['element']}"
		record_id = int(request.data['index'])
		key = (settings.AEROSPIKE_NAMESPACE, record_set, record_id)
		_, meta = aerospike.exists(key)

		if meta is not None:
			return Response(status=HTTP_442_ALREADY_EXIST)
		element = Element.objects.filter(slug=kwargs['element']).first()
		counters = Counter.objects.filter(element=element)
		bins = {'key': record_id}
		for counter in counters:
			bins[f"{counter.slug}"] = 0
			bins[f"{counter.slug}Max"] = counter.max_value
		aerospike.put(key, bins)

		return Response(status=status.HTTP_201_CREATED)


class CounterListCreateApiView(ListCreateAPIView):
	serializer_class = CounterSerializer

	def get_queryset(self):
		platform = Platform.objects.filter(slug=self.kwargs['platform']).first()
		element = Element.objects.filter(platform=platform, slug=self.kwargs['element']).first()
		return Counter.objects.filter(element=element)

	def perform_create(self, serializer):
		"""todo validation for bin name less than 14 characters"""
		slug = slugify(serializer.validated_data['name'])
		platform = Platform.objects.filter(slug=self.kwargs['platform']).first()
		element = Element.objects.filter(platform=platform, slug=self.kwargs['element']).first()

		record_set = f"{platform.slug}/{element.slug}"
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE, record_set)
		query.foreach(get_add_counter_to_record(slug, serializer.validated_data['max_value']))

		serializer.save(element=element, slug=slug)


class CounterDetailApiView(RetrieveUpdateDestroyAPIView):
	serializer_class = CounterSerializer
	lookup_url_kwarg = 'counter'
	lookup_field = 'slug'

	def get_queryset(self):
		platform = Platform.objects.filter(slug=self.kwargs['platform']).first()
		element = Element.objects.filter(platform=platform, slug=self.kwargs['element']).first()
		return Counter.objects.filter(element=element)

	def perform_update(self, serializer):
		"""todo validation for bin name less than 14 characters"""
		obj = self.get_object()
		name = serializer.validated_data.get('name')
		max_value = serializer.validated_data.get('max_value')
		set_name = f"{self.kwargs['platform']}/{self.kwargs['element']}"
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE, set_name)
		if name is not None and name != obj.name:
			slug = slugify(name)
		else:
			slug = obj.slug

		if max_value is not None and max_value != obj.max_value:
			query.foreach(get_update_counter_max_value(obj.slug, max_value))
		if slug != obj.slug:
			query.foreach(get_update_counter_name(obj.slug, slug))

		serializer.save(slug=slug)

	def perform_destroy(self, instance):
		set_name = f"{self.kwargs['platform']}/{self.kwargs['element']}"
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE, set_name)
		query.foreach(get_delete_counter(self.kwargs['counter']))


class CounterActionsApiView(APIView):
	def get(self, request, *args, **kwargs):
		set_name = f"{kwargs['platform']}/{kwargs['element']}"
		try:
			key = (settings.AEROSPIKE_NAMESPACE, set_name, kwargs['uid'])
			_, _, bins = aerospike.get(key)
			result = bins.get(kwargs['counter'])
		except (exception.AerospikeError, KeyError):
			return Response(status=status.HTTP_400_BAD_REQUEST)
		else:
			return Response(result, status=status.HTTP_200_OK)

	def post(self, request, *args, **kwargs):
		set_name = f"{kwargs['platform']}/{kwargs['element']}"
		key = (settings.AEROSPIKE_NAMESPACE, set_name, kwargs['uid'])
		counter = kwargs['counter']

		try:
			value = int(request.data.get('value'))
		except ValueError:
			return Response(status=status.HTTP_400_BAD_REQUEST)
		try:
			_, _, bins = aerospike.get(key)
			if counter not in bins:
				raise KeyError()
		except (exception.AerospikeError, KeyError):
			return Response(status=HTTP_441_NOT_EXIST)

		if bins[counter] + value > bins[f"{counter}Max"]:
			return Response(status=HTTP_440_FULL)

		aerospike.increment(key, kwargs['counter'], value)
		return Response(status=status.HTTP_200_OK)
