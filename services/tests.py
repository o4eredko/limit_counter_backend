import json

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.reverse import reverse
from aerospike import exception

from services import aerospike_db
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

	def test_create_error_name_reserved(self):
		data = {'name': 'Platforms'}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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

	def test_create_error_name_reserved(self):
		data = {'name': 'Elements'}
		response = self.client.post(self.element_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
		cls.element = Element.objects.create(
			name='Test Element', slug='test-element', platform=cls.platform)
		cls.element2 = Element.objects.create(
			name='Test Element2', slug='test-element2', platform=cls.platform)
		cls.counter = Counter.objects.create(
			name='Test Counter', slug='test-counter', max_value=50, element=cls.element)
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

	def test_create_error_name_reserved(self):
		data = {'name': 'Platforms'}
		response = self.client.post(self.counter_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

		data = {'name': 'Records'}
		response = self.client.post(self.counter_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_error_name_exists(self):
		data = {'name': self.counter.name, 'max_value': 50}
		response = self.client.post(self.counter_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_error_invalid_max_value(self):
		data = {'name': 'Counter With Invalid Max Value', 'max_value': 0}
		response = self.client.post(self.counter_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_update_name(self):
		counter = Counter.objects.create(
			name='Counter', slug='counter', max_value=50, element=self.element)
		reverse_kwargs = {
			'platform': self.platform.slug, 'element': self.element.slug, 'counter': counter.slug
		}
		data = {'name': 'Changed Name'}
		url = reverse('counter-detail', kwargs=reverse_kwargs)
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['name'], data['name'])

	def test_delete(self):
		counter = Counter.objects.create(
			name='Counter', slug='counter', max_value=5, element=self.element)
		reverse_kwargs = {
			'platform': self.platform.slug, 'element': self.element.slug, 'counter': counter.slug
		}
		url = reverse('counter-detail', kwargs=reverse_kwargs)
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


@override_settings(AEROSPIKE_NS='test')
class TestRecords(TestCase):
	@classmethod
	def setUpTestData(cls):
		name = 'Test Records'
		slug = 'test-records'
		cls.platform = Platform.objects.create(name=name, slug=slug)
		cls.element = Element.objects.create(name=name, slug=slug, platform=cls.platform)
		cls.records_url = reverse('record-list', kwargs={'platform': slug, 'element': slug})

	def setUp(self) -> None:
		self.added_records = []

	def test_url_accessible_by_name(self):
		response = self.client.get(self.records_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create(self):
		data = {'value': 1}
		response = self.client.post(self.records_url, data)
		self.added_records.append((f"{self.platform.slug}/{self.element.slug}", data['value']))
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_create_error_record_exists(self):
		self.test_create()
		response = self.client.post(self.records_url, {'value': 1})
		self.assertEqual(response.status_code, HTTP_442_ALREADY_EXIST)

	def test_create_error_invalid_index(self):
		response = self.client.post(self.records_url, {'value': 'abc'})
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def tearDown(self) -> None:
		for set_name, key in self.added_records:
			try:
				aerospike_db.remove((settings.AEROSPIKE_NS, set_name, key))
			except exception.AerospikeError:
				pass


@override_settings(AEROSPIKE_NS='test')
class TestCounterActions(TestCase):
	@classmethod
	def setUpTestData(cls):
		name = 'Test Counter Actions'
		slug = 'test-counter-actions'
		cls.platform = Platform.objects.create(name=name, slug=slug)
		cls.element = Element.objects.create(name=name, slug=slug, platform=cls.platform)
		cls.counter = Counter.objects.create(
			name=name, slug=slug, max_value=20, element=cls.element
		)
		cls.records_url = reverse('record-list', kwargs={'platform': slug, 'element': slug})

	def setUp(self) -> None:
		self.added_records = []
		data = {'value': 2}
		response = self.client.post(self.records_url, data)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.added_records.append((f"{self.platform.slug}/{self.element.slug}", data['value']))

		self.reverse_kwargs = {
			'platform': self.platform.slug,
			'element': self.element.slug,
			'uid': data['value'],
			'counter': self.counter.slug,
		}
		self.counter_actions_url = reverse('counter-actions', kwargs=self.reverse_kwargs)

	def test_create_counter(self):
		data = {'name': 'Test Counter Actions2', 'max_value': 50}
		reverse_kwargs = {'platform': self.platform.slug, 'element': self.element.slug}
		url = reverse('counter-list', kwargs=reverse_kwargs)
		new_counter = self.client.post(url, data)
		self.assertEqual(new_counter.status_code, status.HTTP_201_CREATED)

		self.reverse_kwargs['counter'] = new_counter.data['slug']
		url = reverse('counter-actions', kwargs=self.reverse_kwargs)
		response = self.client.post(url, {'value': data['max_value']})
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, data['max_value'])

	def test_delete_counter(self):
		data = {'name': 'Test Counter Actions2', 'max_value': 50}
		reverse_kwargs = {'platform': self.platform.slug, 'element': self.element.slug}
		url = reverse('counter-list', kwargs=reverse_kwargs)
		new_counter = self.client.post(url, data)
		reverse_kwargs['counter'] = new_counter.data['slug']

		url = reverse('counter-detail', kwargs=reverse_kwargs)
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
		reverse_kwargs['uid'] = self.reverse_kwargs['uid']
		response = self.client.get(reverse('counter-actions', kwargs=reverse_kwargs))
		self.assertEqual(response.status_code, HTTP_441_NOT_EXIST)

	def test_get_counter(self):
		response = self.client.get(self.counter_actions_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, 0)

	def test_get_counter_error_not_exist(self):
		self.reverse_kwargs['uid'] = 2147483647
		response = self.client.get(reverse('counter-actions', kwargs=self.reverse_kwargs))
		self.assertEqual(response.status_code, HTTP_441_NOT_EXIST)

	def test_increment_counter(self):
		response = self.client.post(self.counter_actions_url, {'value': self.counter.max_value})
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_increment_counter_error_invalid_value(self):
		response = self.client.post(self.counter_actions_url, {'value': 'string'})
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_increment_error_negative_value(self):
		response = self.client.post(self.counter_actions_url, {'value': -1})
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_increment_counter_error_overflow(self):
		data = {'value': self.counter.max_value + 1}
		response = self.client.post(self.counter_actions_url, data)
		self.assertEqual(response.status_code, HTTP_440_FULL)

	def test_get_after_increment_counter(self):
		data = {'value': self.counter.max_value}
		response = self.client.post(self.counter_actions_url, data)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, data['value'])

		response = self.client.get(self.counter_actions_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, data['value'])

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
				aerospike_db.remove((settings.AEROSPIKE_NS, set_name, key))
			except exception.AerospikeError:
				pass


@override_settings(AEROSPIKE_NS='test')
class TestAerospikeChangeSet(TestCase):
	def setUp(self) -> None:
		self.added_records = []

		name = 'Test Change Set'
		slug = 'test-change-set'
		self.platform = Platform.objects.create(name=name, slug=slug)
		self.element = Element.objects.create(name=name, slug=slug, platform=self.platform)
		self.element2 = Element.objects.create(
			name='Test Change Set2', slug='test-change-set-2', platform=self.platform
		)

		reverse_kwargs = {'platform': self.platform.slug, 'element': self.element.slug}
		self.client.post(reverse('record-list', kwargs=reverse_kwargs), {'value': 42})
		self.added_records.append((f"{self.platform.slug}/{self.element.slug}", 42))

		reverse_kwargs['element'] = self.element2.slug
		self.client.post(reverse('record-list', kwargs=reverse_kwargs), {'value': 42})
		self.added_records.append((f"{self.platform.slug}/{self.element2.slug}", 42))

	def delete_structure(self, url):
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

	def test_delete_platform(self):
		url = reverse('platform-detail', kwargs={'platform': self.platform.slug})
		self.delete_structure(url)

		set_name = f"{self.platform.slug}/{self.element.slug}"
		results = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
		self.assertEqual(len(results), 0)

		set_name = f"{self.platform.slug}/{self.element2.slug}"
		results = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
		self.assertEqual(len(results), 0)

	def test_delete_element(self):
		url = reverse('element-detail', kwargs={
			'platform': self.platform.slug, 'element': self.element.slug
		})
		self.delete_structure(url)

		set_name = f"{self.platform.slug}/{self.element.slug}"
		results = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
		self.assertEqual(len(results), 0)

		set_name = f"{self.platform.slug}/{self.element2.slug}"
		results = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
		self.assertNotEqual(len(results), 0)

	def update_structure(self, url):
		data = {'name': 'Updated Name'}
		response = self.client.patch(url, json.dumps(data), content_type='application/json')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['name'], data['name'])
		return response

	def test_change_platform_name(self):
		# records in platform before update
		platform_records = []
		elements = Element.objects.filter(platform=self.platform)
		for element in elements:
			set_name = f"{self.platform.slug}/{element.slug}"
			records = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
			platform_records.append(records)

		url = reverse('platform-detail', kwargs={'platform': self.platform.slug})
		response = self.update_structure(url)

		for i, element in enumerate(elements):
			set_name = f"{self.platform.slug}/{element.slug}"
			records = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
			self.assertEqual(len(records), 0)

		# compare records in updated platform with old ones
		for i, element in enumerate(elements):
			set_name = f"{response.data['slug']}/{element.slug}"
			records = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
			self.assertEqual(len(records), len(platform_records[i]))
			self.added_records.append((set_name, 42))

	def test_change_element_name(self):
		# records in element before update
		set_name = f"{self.platform.slug}/{self.element.slug}"
		element_records = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()

		url = reverse('element-detail', kwargs={
			'platform': self.platform.slug, 'element': self.element.slug
		})
		response = self.update_structure(url)

		set_name = f"{self.platform.slug}/{self.element.slug}"
		records = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
		self.assertEqual(len(records), 0)

		# change does not affect another element inside the same platform
		set_name = f"{self.platform.slug}/{self.element2.slug}"
		records = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
		self.assertNotEqual(len(records), 0)

		# compare records in updated element with old ones
		set_name = f"{self.platform.slug}/{response.data['slug']}"
		records = aerospike_db.scan(settings.AEROSPIKE_NS, set_name).results()
		self.assertEqual(len(records), len(element_records))
		self.added_records.append((set_name, 42))

	def tearDown(self) -> None:
		for set_name, key in self.added_records:
			try:
				aerospike_db.remove((settings.AEROSPIKE_NS, set_name, key))
			except exception.AerospikeError:
				pass
