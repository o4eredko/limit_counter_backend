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


#
# def delete_record(record):
# 	key, _, _ = record
# 	aerospike.remove(key)

def add_counter_to_record(counter_id):
	def wrapper(record):
		key, _, _ = record
		aerospike.put(key, {counter_id: 0})

	return wrapper


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


def delete_counter(counter_id):
	def wrapper(record):
		key, _, _ = record
		aerospike.remove_bin(key, [counter_id])

	return wrapper


def update_set_name(old_name_part, new_name_part):
	def wrapper(record):
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

	return wrapper


def delete_set(*, platform=None, element=None):
	def wrapper(record):
		key, _, bins = record
		_, set_name, *_ = key
		name_parts = set_name.split('/')
		if platform is not None and platform in name_parts:
			aerospike.remove(key)
		elif element is not None and element == name_parts[1]:
			aerospike.remove(key)

	return wrapper


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
		callback_func = update_set_name(obj.slug, slug)
		query.foreach(callback_func)
		serializer.save(slug=slug)

	def perform_destroy(self, instance):
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE)
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
		slug = slugify(serializer.validated_data['name'])
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE)
		callback_func = update_set_name(obj.slug, slug)
		query.foreach(callback_func)
		serializer.save(slug=slug)

	def perform_destroy(self, instance):
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE)
		callback_func = delete_set(element=instance.slug)
		query.foreach(callback_func)
		instance.delete()

	def post(self, request, *args, **kwargs):
		try:
			record_id = int(request.data['index'])
		except (KeyError, ValueError):
			return Response({'index': 'must be an Integer'}, status=status.HTTP_400_BAD_REQUEST)

		element_slug = kwargs['element']
		platform_slug = kwargs['platform']
		key = (settings.AEROSPIKE_NAMESPACE, f"{platform_slug}/{element_slug}", record_id)
		_, meta = aerospike.exists(key)
		if meta is not None:
			return Response(status=HTTP_442_ALREADY_EXIST)

		element = Element.objects.filter(platform__slug=platform_slug, slug=element_slug).first()
		counters = Counter.objects.filter(element=element)
		bins = {'key': record_id}
		for counter in counters:
			bins[str(counter.id)] = 0
		aerospike.put(key, bins)
		return Response(status=status.HTTP_201_CREATED)


class CounterListCreateApiView(ListCreateAPIView):
	serializer_class = CounterSerializer

	def get_queryset(self):
		return Counter.objects.filter(element__platform__slug=self.kwargs['platform'],
									  element__slug=self.kwargs['element'])

	def perform_create(self, serializer):
		slug = slugify(serializer.validated_data['name'])
		element_slug = self.kwargs['element']
		platform_slug = self.kwargs['platform']
		element = Element.objects.filter(platform__slug=platform_slug, slug=element_slug).first()
		serializer.save(element=element, slug=slug)

		query = aerospike.query(settings.AEROSPIKE_NAMESPACE, f"{platform_slug}/{element_slug}")
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
		slug = slugify(serializer.validated_data['name'])
		serializer.save(slug=slug)

	def perform_destroy(self, instance):
		set_name = f"{self.kwargs['platform']}/{self.kwargs['element']}"
		query = aerospike.query(settings.AEROSPIKE_NAMESPACE, set_name)
		callback_func = delete_counter(instance.id)
		query.foreach(callback_func)
		instance.delete()


class CounterActionsApiView(APIView):
	def get(self, request, *args, **kwargs):
		element_slug = kwargs['element']
		platform_slug = kwargs['platform']
		key = (settings.AEROSPIKE_NAMESPACE, f"{platform_slug}/{element_slug}", kwargs['uid'])
		counter = Counter.objects.filter(element__platform__slug=platform_slug,
										 element__slug=element_slug, slug=kwargs['counter']).first()
		try:
			_, _, bins = aerospike.get(key)
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
		counter = Counter.objects.filter(element__slug=element_slug, slug=kwargs['counter']).first()
		try:
			_, _, bins = aerospike.get(key)
			counter_value = bins[str(counter.id)]
		except (exception.AerospikeError, KeyError):
			return Response(status=HTTP_441_NOT_EXIST)

		if counter_value + value > counter.max_value:
			return Response(status=HTTP_440_FULL)
		aerospike.increment(key, str(counter.id), value)
		return Response(status=status.HTTP_200_OK)
