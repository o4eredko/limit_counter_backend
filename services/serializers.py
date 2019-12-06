from rest_framework import serializers

from services.models import Platform, Element


class PlatformSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = Platform
		fields = ('url', 'name')


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
