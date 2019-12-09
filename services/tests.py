from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse


class TestPlatforms(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.platform_list_url = reverse('platform-list')
		cls.platform_detail_url = reverse('platform-detail',
										  kwargs={'platform': 'google'})

	def setUp(self) -> None:
		self.client.post(self.platform_list_url, {'name': 'Google'})

	def test_create_platform_error_name_exists(self):
		data = {'name': 'Google'}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_create_platform_error_slug_exists(self):
		data = {'name': 'google'}
		response = self.client.post(self.platform_list_url, data)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_delete_platform(self):
		response = self.client.delete(self.platform_detail_url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
