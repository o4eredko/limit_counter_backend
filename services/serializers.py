from rest_framework import serializers

from services.models import Platform, Element


class PlatformSerializer(serializers.ModelSerializer):
	class Meta:
		model = Platform
		fields = ('id', 'name')


class ElementSerializer(serializers.ModelSerializer):
	platform = serializers.PrimaryKeyRelatedField(queryset=Platform.objects.all())

	class Meta:
		model = Platform
		fields = ('id', 'name', 'platform')


class CounterSerializer(serializers.ModelSerializer):
	max_value = serializers.IntegerField(min_value=0)
	element = serializers.PrimaryKeyRelatedField(queryset=Element.objects.all())

	class Meta:
		model = Platform
		fields = ('id', 'name', 'max_value', 'element')
