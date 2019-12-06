from rest_framework import serializers

from services.models import Platform, Element


class PlatformListCreateSerializer(serializers.ModelSerializer):
	class Meta:
		model = Platform
		lookup_field = 'name'
		fields = ('url', 'name')
		extra_kwargs = {
			'url': {'lookup_field': 'name'}
		}

	def validate(self, attrs):
		name = attrs['name'].lower()
		if Platform.objects.filter(name=name).exists():
			raise serializers.ValidationError({'name': "This field must be unique in lowercase"})
		attrs['name'] = name
		return attrs


class PlatformDetailSerializer(serializers.ModelSerializer):
	class Meta:
		model = Platform
		fields = ('url', 'name')
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


class ElementSerializer(serializers.HyperlinkedModelSerializer):
	platform = serializers.PrimaryKeyRelatedField(queryset=Platform.objects.all())
	platform_name = serializers.CharField(source='platform.name', read_only=True)

	class Meta:
		model = Element
		fields = ('url', 'name', 'platform', 'platform_name')

#
# class CounterSerializer(serializers.ModelSerializer):
# 	max_value = serializers.IntegerField(min_value=0)
# 	element = serializers.PrimaryKeyRelatedField(queryset=Element.objects.all())
#
# 	class Meta:
# 		model = Platform
# 		fields = ('id', 'name', 'max_value', 'element')
