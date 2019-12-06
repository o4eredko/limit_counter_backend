from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

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
		if Platform.objects.filter(name=value).exists():
			raise ValidationError("must be unique")
		elif Platform.objects.filter(slug=slug).exists():
			raise ValidationError("avoid similar names i.e (Google google, face-book Face Book)")
		return value


class ElementSerializer(serializers.ModelSerializer):
	url = serializers.SerializerMethodField()
	slug = serializers.ReadOnlyField()
	counters_url = serializers.SerializerMethodField()

	class Meta:
		model = Element
		fields = ('name', 'slug', 'url', 'counters_url')

	def get_url(self, obj):
		request = self.context.get('request')
		url = reverse('element-detail', kwargs={'platform': obj.platform.slug, 'element': obj.slug})
		return request.build_absolute_uri(url)

	def get_counters_url(self, obj):
		request = self.context.get('request')
		url = reverse('counter-list', kwargs={'platform': obj.platform.slug, 'element': obj.slug})
		return request.build_absolute_uri(url)

	def validate_name(self, value):
		slug = slugify(value)
		platform_slug = self.context['view'].kwargs.get('platform')
		platform = Platform.objects.filter(slug=platform_slug).first()
		if Element.objects.filter(platform=platform, name=value).exists():
			raise ValidationError("must be unique inside each platform")
		elif Element.objects.filter(platform=platform, slug=slug).exists():
			raise ValidationError("avoid similar names i.e (Google google, face-book Face Book)")
		return value


class CounterSerializer(serializers.ModelSerializer):
	slug = serializers.ReadOnlyField()
	url = serializers.SerializerMethodField()

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

		platform_slug = self.context['view'].kwargs.get('platform')
		platform = Platform.objects.filter(slug=platform_slug).first()
		element_slug = self.context['view'].kwargs.get('element')
		element = Element.objects.filter(platform=platform, slug=element_slug).first()

		if Counter.objects.filter(element=element, name=value).exists():
			raise ValidationError("must be unique inside each element")
		elif Counter.objects.filter(element=element, slug=slug).exists():
			raise ValidationError("avoid similar names i.e (Google google, face-book Face Book)")
		return value
