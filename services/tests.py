import json

from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from limit_counter import settings
from services import aerospike
from services.models import Platform, Element, Counter
from services.views import HTTP_441_NOT_EXIST, HTTP_440_FULL, HTTP_442_ALREADY_EXIST


class TestPlatforms(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.google = Platform.objects.create(name='Google', slug='google')
		cls.platform_list_url = reverse('platform-list')

	def test_url_accessible_by_name(self):
		response = self.client.get(self.platform_list_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

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
		yahoo = Platform.objects.create(name='Yahoo', slug='yahoo')
		url = reverse('platform-detail', kwargs={'platform': yahoo.slug})
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestElements(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.google = Platform.objects.create(name='Google', slug='google')
		cls.mozilla = Platform.objects.create(name='Mozilla', slug='mozilla')
		cls.account = Element.objects.create(name='Account', slug='account', platform=cls.google)
		cls.google_list_url = reverse('element-list', kwargs={'platform': cls.google.slug})

	def test_url_accessible_by_name(self):
		response = self.client.get(self.google_list_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

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
		ad_groups = Element.objects.create(name='Ad Groups', slug='ad-groups', platform=self.google)
		url = reverse('element-detail', kwargs={'platform': self.google.slug,
												'element': ad_groups.slug})
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestCounters(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.platform = Platform.objects.create(name='Test Platform', slug='test-platform')
		cls.account = Element.objects.create(name='Account', slug='account', platform=cls.platform)
		cls.group = Element.objects.create(name='Group', slug='group', platform=cls.platform)
		cls.ads = Counter.objects.create(name='Ads', slug='ads', max_value=50, element=cls.account)
		cls.account_list_url = reverse('counter-list', kwargs={'platform': cls.platform.slug,
															   'element': cls.account.slug})

	def test_url_accessible_by_name(self):
		response = self.client.get(self.account_list_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create(self):
		data = {'name': 'Counter', 'max_value': 50}
		response = self.client.post(self.account_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_name_exists_in_another_element(self):
		data = {'name': self.ads.name, 'max_value': 50}
		url = reverse('counter-list', kwargs={'platform': self.platform.slug,
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

	def test_update_name(self):
		counter = Counter.objects.create(name='Counter', slug='counter',
										 max_value=50, element=self.account)
		reverse_kwargs = {
			'platform': self.platform.slug, 'element': self.account.slug, 'counter': counter.slug
		}
		data = {'name': 'Changed Name'}
		url = reverse('counter-detail', kwargs=reverse_kwargs)
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['name'], data['name'])

	def test_delete(self):
		counter = Counter.objects.create(name='Counter', slug='counter',
										 max_value=5, element=self.account)
		reverse_kwargs = {
			'platform': self.platform.slug, 'element': self.account.slug, 'counter': counter.slug
		}
		url = reverse('counter-detail', kwargs=reverse_kwargs)
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestAerospike(TestCase):
	# todo tests to increment, get counter, number
	@classmethod
	def setUpTestData(cls):
		cls.platform = Platform.objects.create(name='Test Platform', slug='test-platform')
		cls.account = Element.objects.create(name='Account', slug='account', platform=cls.platform)
		cls.ads = Counter.objects.create(name='Ads', max_value=20, slug='ads', element=cls.account)

	def setUp(self) -> None:
		self.added_records = []
		url = reverse('element-detail', kwargs={'platform': self.platform.slug,
												'element': self.account.slug})
		data = {'index': 42}
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.added_records.append((f"{self.platform.slug}/{self.account.slug}", data['index']))
		self.record_id = data['index']
		self.reverse_kwargs = {
			'platform': self.platform.slug,
			'element': self.account.slug,
			'uid': self.record_id,
			'counter': self.ads.slug,
		}

	def test_create_record_error_already_exist(self):
		url = reverse('element-detail', kwargs={'platform': self.platform.slug,
												'element': self.account.slug})
		data = {'index': self.record_id}
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, HTTP_442_ALREADY_EXIST)

	def test_get_counter(self):
		response = self.client.get(reverse('counter-actions', kwargs=self.reverse_kwargs))
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, 0)

	def test_get_counter_error_wrong_record_id(self):
		self.reverse_kwargs['uid'] = 2147483647
		response = self.client.get(reverse('counter-actions', kwargs=self.reverse_kwargs))
		self.assertEqual(response.status_code, HTTP_441_NOT_EXIST)

	def test_increment_counter(self):
		data = {'value': self.ads.max_value - 1}
		response = self.client.post(reverse('counter-actions', kwargs=self.reverse_kwargs), data)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_increment_counter_error_wrong_value(self):
		data = {'value': 'string'}
		response = self.client.post(reverse('counter-actions', kwargs=self.reverse_kwargs), data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_increment_counter_error_overflow(self):
		data = {'value': self.ads.max_value + 1}
		response = self.client.post(reverse('counter-actions', kwargs=self.reverse_kwargs), data)
		self.assertEqual(response.status_code, HTTP_440_FULL)

	def test_get_after_increment_counter(self):
		data = {'value': self.ads.max_value - 1}
		response = self.client.post(reverse('counter-actions', kwargs=self.reverse_kwargs), data)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		response = self.client.get(reverse('counter-actions', kwargs=self.reverse_kwargs))
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, data['value'])

	def tearDown(self) -> None:
		for set_name, key in self.added_records:
			aerospike.remove((settings.AEROSPIKE_NAMESPACE, set_name, key))
#
