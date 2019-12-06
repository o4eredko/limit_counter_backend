from rest_framework import serializers
from rest_framework.reverse import reverse

from services.models import Platform, Element


class PlatformListCreateSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = Platform
		fields = ('name', 'url')
		extra_kwargs = {
			'url': {'lookup_url_kwarg': 'platform', 'lookup_field': 'name'},
		}

	def validate_name(self, value):
		value = value.lower()
		if self.Meta.model.objects.filter(name=value).exists():
			raise serializers.ValidationError("This field must be unique in lowercase")
		return value


class PlatformDetailSerializer(serializers.HyperlinkedModelSerializer):
	elements_url = serializers.SerializerMethodField()

	class Meta:
		model = Platform
		fields = ('name', 'url', 'elements_url')
		extra_kwargs = {
			'url': {'lookup_url_kwarg': 'platform', 'lookup_field': 'name'},
		}

	def get_elements_url(self, obj):
		request = self.context.get('request')
		url = reverse('element-list', kwargs={'platform': obj.name})
		return request.build_absolute_uri(url)

	def validate_name(self, value):
		name = value.lower()
		if self.Meta.model.objects.filter(name=name).exists():
			raise serializers.ValidationError("This field must be unique in lowercase")
		return name


class ElementListCreateSerializer(serializers.HyperlinkedModelSerializer):
	url = serializers.SerializerMethodField()

	class Meta:
		model = Element
		fields = ('name', 'url')
		extra_kwargs = {
			'url': {'lookup_url_kwarg': 'element', 'lookup_field': 'name'}
		}

	def get_url(self, obj):
		request = self.context.get('request')
		url = reverse('element-detail', kwargs={'platform': obj.platform.name, 'element': obj.name})
		return request.build_absolute_uri(url)

	def validate_name(self, value):
		value = value.lower()
		if self.Meta.model.objects.filter(name=value).exists():
			raise serializers.ValidationError("This field must be unique in lowercase")
		return value


class ElementDetailSerializer(serializers.ModelSerializer):
	url = serializers.SerializerMethodField()

	class Meta:
		model = Element
		fields = ('name', 'url')

	def get_url(self, obj):
		request = self.context.get('request')
		url = reverse('element-detail', kwargs={'platform': obj.platform.name, 'element': obj.name})
		return request.build_absolute_uri(url)

	def validate_name(self, value):
		value = value.lower()
		if self.Meta.model.objects.filter(name=value).exists():
			raise serializers.ValidationError("This field must be unique in lowercase")
		return value
