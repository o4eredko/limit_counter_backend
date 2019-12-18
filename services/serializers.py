from django.utils.text import slugify
from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from services import aerospike_db
from services.aerospike_utils import check_counter_overflow
from services.models import Platform, Element, Counter


class PlatformSerializer(serializers.HyperlinkedModelSerializer):
	slug = serializers.ReadOnlyField()
	elements_url = serializers.SerializerMethodField()

	class Meta:
		model = Platform
		fields = ('name', 'slug', 'url', 'elements_url')
		extra_kwargs = {
			'url': {'lookup_url_kwarg': 'platform', 'lookup_field': 'slug'},
		}

	def get_elements_url(self, obj):
		request = self.context.get('request')
		url = reverse('element-list', kwargs={'platform': obj.slug})
		return request.build_absolute_uri(url)

	def validate_name(self, value):
		slug = slugify(value)
		if self.instance is not None and self.instance.slug == slug:
			return value
		if slug == "platforms":
			raise ValidationError("cannot add platform with reserved name")
		elif Platform.objects.filter(name=value).exists():
			raise ValidationError("must be unique")
		elif Platform.objects.filter(slug=slug).exists():
			raise ValidationError("avoid similar names i.e (Google google, face-book Face Book)")
		return value


class ElementSerializer(serializers.ModelSerializer):
	url = serializers.SerializerMethodField()
	slug = serializers.ReadOnlyField()
	counters_url = serializers.SerializerMethodField()
	records_url = serializers.SerializerMethodField()

	class Meta:
		model = Element
		fields = ('name', 'slug', 'url', 'counters_url', 'records_url')

	def get_url(self, obj):
		request = self.context.get('request')
		url = reverse('element-detail', kwargs={'platform': obj.platform.slug, 'element': obj.slug})
		return request.build_absolute_uri(url)

	def get_counters_url(self, obj):
		request = self.context.get('request')
		url = reverse('counter-list', kwargs={'platform': obj.platform.slug, 'element': obj.slug})
		return request.build_absolute_uri(url)

	def get_records_url(self, obj):
		request = self.context.get('request')
		url = reverse('record-list', kwargs={'platform': obj.platform.slug, 'element': obj.slug})
		return request.build_absolute_uri(url)

	def validate_name(self, value):
		slug = slugify(value)
		if self.instance is not None and self.instance.slug == slug:
			return value
		platform_slug = self.context['view'].kwargs.get('platform')

		if slug == "elements":
			raise ValidationError("cannot add element with reserved name")
		elif Element.objects.filter(platform__slug=platform_slug, name=value).exists():
			raise ValidationError("must be unique inside each platform")
		elif Element.objects.filter(platform__slug=platform_slug, slug=slug).exists():
			raise ValidationError("avoid similar names i.e (Ad Groups and ad-groups)")
		return value


class CounterSerializer(serializers.ModelSerializer):
	url = serializers.SerializerMethodField()
	slug = serializers.ReadOnlyField()
	max_value = serializers.IntegerField(min_value=1)

	class Meta:
		model = Counter
		fields = ('id', 'name', 'slug', 'max_value', 'url')

	def get_url(self, obj):
		request = self.context.get('request')
		url = reverse('counter-detail', kwargs={'platform': obj.element.platform.slug,
												'element': obj.element.slug,
												'counter': obj.slug})
		return request.build_absolute_uri(url)

	def validate_name(self, value):
		slug = slugify(value)
		if self.instance is not None and self.instance.slug == slug:
			return value
		element_slug = self.context['view'].kwargs.get('element')
		platform_slug = self.context['view'].kwargs.get('platform')
		element = Element.objects.filter(platform__slug=platform_slug, slug=element_slug).first()
		if slug == "counters" or slug == "records":
			raise ValidationError("cannot add counter with reserved name")
		elif Counter.objects.filter(element=element, name=value).exists():
			raise ValidationError("must be unique inside each element")
		elif Counter.objects.filter(element=element, slug=slug).exists():
			raise ValidationError("avoid similar names i.e (Group Counter, group-counter)")
		return value

	def validate_max_value(self, value):
		if self.instance is None or self.instance.max_value == value:
			return value
		element_slug = self.context['view'].kwargs.get('element')
		platform_slug = self.context['view'].kwargs.get('platform')
		set_name = f"{platform_slug}/{element_slug}"

		query = aerospike_db.query(settings.AEROSPIKE_NAMESPACE, set_name)
		callback_func = check_counter_overflow(self.instance.id, value)
		query.foreach(callback_func)
		if callback_func(get_overflow=True):
			error_message = ('You cannot change it, because it will cause an '
							 'overflow for counter in records that already exist')
			raise ValidationError(error_message)
		return value
