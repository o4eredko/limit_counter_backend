from rest_framework import serializers

from services.models import Platform, Element


class PlatformListCreateSerializer(serializers.ModelSerializer):
	url = serializers.HyperlinkedIdentityField(view_name='platform-detail',
											   lookup_url_kwarg='platform', lookup_field='name')

	class Meta:
		model = Platform
		lookup_field = 'name'
		fields = ('name', 'url')

	def validate(self, attrs):
		attrs['name'] = attrs['name'].lower()
		if self.Meta.model.objects.filter(name=attrs['name']).exists():
			raise serializers.ValidationError({'name': "This field must be unique in lowercase"})
		return attrs


class PlatformDetailSerializer(serializers.ModelSerializer):
	url = serializers.HyperlinkedIdentityField(view_name='platform-detail',
											   lookup_url_kwarg='platform', lookup_field='name')

	# elements = serializers.PrimaryKeyRelatedField(many=True)
	class Meta:
		model = Platform
		fields = ('name', 'url')
		lookup_field = 'platform'

	def validate(self, attrs):
		name = attrs['name'].lower()
		if self.Meta.model.objects.filter(name=name).exists():
			raise serializers.ValidationError({'name': "This field must be unique in lowercase"})
		attrs['name'] = name
		return attrs


class ElementListCreateSerializer(serializers.ModelSerializer):
	platform = serializers.ReadOnlyField(source='platform.name')

	class Meta:
		model = Element
		fields = ('name', 'url', 'platform')
		lookup_field = 'name'
		extra_kwargs = {
			'url': {'lookup_field': 'name'}
		}

	def validate(self, attrs):
		name = attrs['name'].lower()
		if Platform.objects.filter(name=name).exists():
			raise serializers.ValidationError({'name': "This field must be unique in lowercase"})
		attrs['name'] = name
		return attrs
