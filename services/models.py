from django.db import models


class Platform(models.Model):
	name = models.CharField(max_length=20, unique=True)
	slug = models.SlugField(max_length=20, unique=True)

	def __str__(self):
		return self.slug


class Element(models.Model):
	name = models.CharField(max_length=30)
	slug = models.SlugField(max_length=30)
	platform = models.ForeignKey(to=Platform, related_name='elements', on_delete=models.CASCADE)

	def __str__(self):
		return self.slug


class Counter(models.Model):
	name = models.CharField(max_length=30)
	slug = models.SlugField(max_length=30)
	element = models.ForeignKey(to=Element, related_name='counters', on_delete=models.CASCADE)
	max_value = models.IntegerField(verbose_name='Max value')

	def __str__(self):
		return self.name
