from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from services.models import Platform, Element


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


class ElementListCreateSerializer(serializers.ModelSerializer):
	url = serializers.SerializerMethodField()
	slug = serializers.ReadOnlyField()

	class Meta:
		model = Element
		fields = ('name', 'slug', 'url')

	def get_url(self, obj):
		request = self.context.get('request')
		url = reverse('element-detail', kwargs={'platform': obj.platform.slug, 'element': obj.slug})
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


class ElementDetailSerializer(serializers.ModelSerializer):
	url = serializers.SerializerMethodField()
	slug = serializers.ReadOnlyField()

	class Meta:
		model = Element
		fields = ('name', 'slug', 'url')

	def get_url(self, obj):
		request = self.context.get('request')
		url = reverse('element-detail', kwargs={'platform': obj.platform.slug, 'element': obj.slug})
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
