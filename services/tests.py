from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from services.models import Platform, Element, Counter


class TestPlatforms(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.google = Platform.objects.create(name='Google', slug='google')
		cls.platform_list_url = reverse('platform-list')

	def test_create(self):
		data = {'name': 'Platform'}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_error_name_exists(self):
		data = {'name': self.google.name}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_error_slug_exists(self):
		data = {'name': self.google.slug}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_delete(self):
		url = reverse('platform-detail', kwargs={'platform': self.google.slug})
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestElements(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.google = Platform.objects.create(name='Google', slug='google')
		cls.mozilla = Platform.objects.create(name='Mozilla', slug='mozilla')
		cls.account = Element.objects.create(name='Account', slug='account', platform=cls.google)
		cls.google_list_url = reverse('element-list', kwargs={'platform': cls.google.slug})

	def test_create(self):
		data = {'name': 'Element'}
		response = self.client.post(self.google_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_name_exist_in_another_platform(self):
		data = {'name': self.account.name}
		url = reverse('element-list', kwargs={'platform': self.mozilla.slug})
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_error_name_exists(self):
		data = {'name': self.account.name}
		response = self.client.post(self.google_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_platform_error_slug_exists(self):
		data = {'name': self.account.slug}
		response = self.client.post(self.google_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_delete(self):
		url = reverse('element-detail',
					  kwargs={'platform': self.google.slug, 'element': self.account.slug})
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestCounters(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.google = Platform.objects.create(name='Google', slug='google')
		cls.account = Element.objects.create(name='Account', slug='account', platform=cls.google)
		cls.group = Element.objects.create(name='Group', slug='group', platform=cls.google)
		cls.ads = Counter.objects.create(name='Ads', slug='ads', max_value=50, element=cls.account)
		cls.account_list_url = reverse('counter-list', kwargs={'platform': cls.google.slug,
															   'element': cls.account.slug})

	def test_create(self):
		data = {'name': 'Counter', 'max_value': 50}
		response = self.client.post(self.account_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_name_exists_in_another_element(self):
		data = {'name': self.ads.name, 'max_value': 50}
		url = reverse('counter-list', kwargs={'platform': self.google.slug,
											  'element': self.group.slug})
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_error_name_exists(self):
		data = {'name': self.ads.name, 'max_value': 50}
		response = self.client.post(self.account_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_error_invalid_max_value(self):
		data = {'name': 'Counter', 'max_value': 0}
		response = self.client.post(self.account_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_delete(self):
		url = reverse('counter-detail', kwargs={'platform': self.google.slug,
												'element': self.account.slug,
												'counter': self.ads.slug})
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
