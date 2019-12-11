import json

from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from aerospike import exception

from limit_counter import settings
from services import aerospike
from services.models import Platform, Element, Counter
from services.views import HTTP_441_NOT_EXIST, HTTP_440_FULL, HTTP_442_ALREADY_EXIST


class TestPlatforms(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.platform = Platform.objects.create(name='Test Platform', slug='test-platform')
		cls.platform_list_url = reverse('platform-list')

	def test_url_accessible_by_name(self):
		response = self.client.get(self.platform_list_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create(self):
		data = {'name': 'Platform'}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_error_name_exists(self):
		data = {'name': self.platform.name}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_error_slug_exists(self):
		data = {'name': self.platform.slug}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_update(self):
		platform = Platform.objects.create(name='Platform For Update', slug='platform-to-update')
		url = reverse('platform-detail', kwargs={'platform': platform.slug})
		data = {'name': 'Platform Was Updated'}
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['name'], data['name'])

	def test_delete(self):
		platform = Platform.objects.create(name='Platform To Delete', slug='platform-to-delete')
		url = reverse('platform-detail', kwargs={'platform': platform.slug})
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestElements(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.platform = Platform.objects.create(name='Test Platform', slug='test-platform')
		cls.platform2 = Platform.objects.create(name='Test Platform2', slug='test-platform2')
		cls.element = Element.objects.create(name='Account', slug='account', platform=cls.platform)
		cls.element_list_url = reverse('element-list', kwargs={'platform': cls.platform.slug})

	def test_url_accessible_by_name(self):
		response = self.client.get(self.element_list_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create(self):
		data = {'name': 'Element'}
		response = self.client.post(self.element_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_name_exist_in_another_platform(self):
		data = {'name': self.element.name}
		url = reverse('element-list', kwargs={'platform': self.platform2.slug})
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_error_name_exists(self):
		data = {'name': self.element.name}
		response = self.client.post(self.element_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_platform_error_slug_exists(self):
		data = {'name': self.element.slug}
		response = self.client.post(self.element_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_update(self):
		element = Element.objects.create(name='Element To Update', slug='element-to-update',
										 platform=self.platform)
		reverse_kwargs = {'platform': self.platform.slug, 'element': element.slug}
		url = reverse('element-detail', kwargs=reverse_kwargs)
		data = {'name': 'Element Was Updated'}
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['name'], data['name'])

	def test_delete(self):
		element = Element.objects.create(name='Test Element', slug='test-element',
										 platform=self.platform)
		reverse_kwargs = {'platform': self.platform.slug, 'element': element.slug}
		response = self.client.delete(reverse('element-detail', kwargs=reverse_kwargs))
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestCounters(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.platform = Platform.objects.create(name='Test Platform', slug='test-platform')
		cls.element = Element.objects.create(name='Test Element', slug='test-element',
											 platform=cls.platform)
		cls.element2 = Element.objects.create(name='Test Element2', slug='test-element2',
											  platform=cls.platform)
		cls.counter = Counter.objects.create(name='Test Counter', slug='test-counter', max_value=50,
											 element=cls.element)
		reverse_kwargs = {'platform': cls.platform.slug, 'element': cls.element.slug}
		cls.counter_list_url = reverse('counter-list', kwargs=reverse_kwargs)

	def test_url_accessible_by_name(self):
		response = self.client.get(self.counter_list_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create(self):
		data = {'name': 'Counter', 'max_value': 50}
		response = self.client.post(self.counter_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_name_exists_in_another_element(self):
		data = {'name': self.counter.name, 'max_value': 50}
		reverse_kwargs = {'platform': self.platform.slug, 'element': self.element2.slug}
		url = reverse('counter-list', kwargs=reverse_kwargs)
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_error_name_exists(self):
		data = {'name': self.counter.name, 'max_value': 50}
		response = self.client.post(self.counter_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_error_invalid_max_value(self):
		data = {'name': 'Counter With Invalid Max Value', 'max_value': 0}
		response = self.client.post(self.counter_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_update_name(self):
		counter = Counter.objects.create(name='Counter', slug='counter',
										 max_value=50, element=self.element)
		reverse_kwargs = {
			'platform': self.platform.slug, 'element': self.element.slug, 'counter': counter.slug
		}
		data = {'name': 'Changed Name'}
		url = reverse('counter-detail', kwargs=reverse_kwargs)
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['name'], data['name'])

	def test_delete(self):
		counter = Counter.objects.create(name='Counter', slug='counter',
										 max_value=5, element=self.element)
		reverse_kwargs = {
			'platform': self.platform.slug, 'element': self.element.slug, 'counter': counter.slug
		}
		url = reverse('counter-detail', kwargs=reverse_kwargs)
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestAerospike(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.platform = Platform.objects.create(name='Test Platform', slug='test-platform')
		cls.element = Element.objects.create(name='Test Element', slug='test-element',
											 platform=cls.platform)
		cls.counter = Counter.objects.create(name='Test Counter', slug='test-counter', max_value=20,
											 element=cls.element)

	def setUp(self) -> None:
		self.added_records = []
		url = reverse('element-detail', kwargs={'platform': self.platform.slug,
												'element': self.element.slug})
		data = {'index': 42}
		response = self.client.post(url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.added_records.append((f"{self.platform.slug}/{self.element.slug}", data['index']))
		self.record_id = data['index']
		self.reverse_kwargs = {
			'platform': self.platform.slug,
			'element': self.element.slug,
			'uid': self.record_id,
			'counter': self.counter.slug,
		}

	def test_create_record_error_already_exist(self):
		url = reverse('element-detail', kwargs={'platform': self.platform.slug,
												'element': self.element.slug})
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
		data = {'value': self.counter.max_value}
		response = self.client.post(reverse('counter-actions', kwargs=self.reverse_kwargs), data)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_increment_counter_error_wrong_value(self):
		data = {'value': 'string'}
		response = self.client.post(reverse('counter-actions', kwargs=self.reverse_kwargs), data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_increment_counter_error_overflow(self):
		data = {'value': self.counter.max_value + 1}
		response = self.client.post(reverse('counter-actions', kwargs=self.reverse_kwargs), data)
		self.assertEqual(response.status_code, HTTP_440_FULL)

	def test_get_after_increment_counter(self):
		data = {'value': self.counter.max_value}
		response = self.client.post(reverse('counter-actions', kwargs=self.reverse_kwargs), data)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		response = self.client.get(reverse('counter-actions', kwargs=self.reverse_kwargs))
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, data['value'])

	def test_change_set_name(self):
		platform = Platform.objects.create(name='Platform To Update', slug='platform-to-update')
		element = Element.objects.create(name='Test Element', slug='test-element',
										 platform=platform)

		url = reverse('element-detail', kwargs={'platform': platform.slug, 'element': element.slug})
		response = self.client.post(url, {'index': 1})
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		old_set_name = f"{platform.slug}/{element.slug}"
		self.added_records.append((old_set_name, 1))

		data = {'name': 'Platform Was Updated'}
		url = reverse('platform-detail', kwargs={'platform': platform.slug})
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		new_set_name = f"{response.data['slug']}/{element.slug}"
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.added_records.append((new_set_name, 1))

		_, meta = aerospike.exists((settings.AEROSPIKE_NAMESPACE, old_set_name, 1))
		self.assertIsNone(meta)
		_, meta = aerospike.exists((settings.AEROSPIKE_NAMESPACE, new_set_name, 1))
		self.assertIsNotNone(meta)

	def test_change_counter_max_value(self):
		reverse_kwargs = {
			'platform': self.platform.slug,
			'element': self.element.slug,
			'counter': self.counter.slug,
		}
		url = reverse('counter-detail', kwargs=reverse_kwargs)
		data = {'max_value': self.counter.max_value + 1}
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_change_counter_max_value_error_overflow(self):
		self.test_increment_counter()
		reverse_kwargs = {
			'platform': self.platform.slug,
			'element': self.element.slug,
			'counter': self.counter.slug,
		}
		url = reverse('counter-detail', kwargs=reverse_kwargs)
		data = {'max_value': 5}
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def tearDown(self) -> None:
		for set_name, key in self.added_records:
			try:
				aerospike.remove((settings.AEROSPIKE_NAMESPACE, set_name, key))
			except exception.AerospikeError:
				pass
