from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from todo.models import List, ListItem
import csv
import io

class ImportTodoCSVTestCase(TestCase):

    def setUp(self):
        # Set up a user and login
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # Define the URL for the import view
        self.url = reverse('todo:import_todo_csv')

    def generate_csv_file(self, rows):
        """Utility function to generate a CSV file in memory."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['List Title', 'Item Name', 'Item Text', 'Is Done', 'Created On', 'Due Date'])
        writer.writerows(rows)
        output.seek(0)
        return SimpleUploadedFile('todos.csv', output.read().encode('utf-8'), content_type='text/csv')

    def test_successful_import(self):
        csv_file = self.generate_csv_file([
            ['Test List', 'Sample Item', 'Sample Text', 'True', '2024-10-01', '2024-12-01']
        ])
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertRedirects(response, reverse('todo:index'))
        self.assertTrue(List.objects.filter(title_text='Test List').exists())
        self.assertTrue(ListItem.objects.filter(item_name='Sample Item').exists())

    # def test_missing_file_in_request(self):
    #     response = self.client.post(self.url)
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertEqual(List.objects.count(), 0)

    # def test_empty_csv_file(self):
    #     csv_file = SimpleUploadedFile('empty.csv', b'', content_type='text/csv')
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertEqual(List.objects.count(), 0)

    # def test_missing_header_row(self):
    #     csv_file = self.generate_csv_file([
    #         ['Test List', 'Sample Item', 'Sample Text', 'True', '2024-10-01', '2024-12-01']
    #     ])
    #     csv_file.file.seek(0)  # Rewind to simulate missing header row
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertTrue(List.objects.filter(title_text='Test List').exists())

    # def test_missing_fields_in_row(self):
    #     csv_file = self.generate_csv_file([
    #         ['Test List', 'Sample Item', 'Sample Text', 'True']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertEqual(List.objects.count(), 0)

    # def test_extra_columns_in_row(self):
    #     csv_file = self.generate_csv_file([
    #         ['Test List', 'Sample Item', 'Sample Text', 'True', '2024-10-01', '2024-12-01', 'Extra Column']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertTrue(List.objects.filter(title_text='Test List').exists())

    # def test_invalid_date_format_in_created_on_field(self):
    #     csv_file = self.generate_csv_file([
    #         ['Test List', 'Sample Item', 'Sample Text', 'True', 'invalid-date', '2024-12-01']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertEqual(List.objects.count(), 0)

    # def test_invalid_boolean_value_in_is_done_field(self):
    #     csv_file = self.generate_csv_file([
    #         ['Test List', 'Sample Item', 'Sample Text', 'not-a-boolean', '2024-10-01', '2024-12-01']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertTrue(ListItem.objects.filter(is_done=False).exists())

    # def test_missing_due_date_field(self):
    #     csv_file = self.generate_csv_file([
    #         ['Test List', 'Sample Item', 'Sample Text', 'True', '2024-10-01', '']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertTrue(ListItem.objects.filter(due_date=None).exists())

    # def test_creating_new_lists(self):
    #     csv_file = self.generate_csv_file([
    #         ['New List', 'Sample Item', 'Sample Text', 'True', '2024-10-01', '2024-12-01']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertTrue(List.objects.filter(title_text='New List').exists())

    # def test_updating_existing_lists(self):
    #     List.objects.create(title_text='Existing List')
    #     csv_file = self.generate_csv_file([
    #         ['Existing List', 'New Item', 'New Text', 'True', '2024-10-01', '2024-12-01']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertTrue(ListItem.objects.filter(item_name='New Item').exists())

    # def test_empty_list_title_in_row(self):
    #     csv_file = self.generate_csv_file([
    #         ['', 'Sample Item', 'Sample Text', 'True', '2024-10-01', '2024-12-01']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertEqual(List.objects.count(), 0)

    # def test_maximum_item_name_length(self):
    #     max_length_name = 'A' * 50
    #     csv_file = self.generate_csv_file([
    #         ['Test List', max_length_name, 'Sample Text', 'True', '2024-10-01', '2024-12-01']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertTrue(ListItem.objects.filter(item_name=max_length_name).exists())

    # def test_blank_item_name(self):
    #     csv_file = self.generate_csv_file([
    #         ['Test List', '', 'Sample Text', 'True', '2024-10-01', '2024-12-01']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertTrue(ListItem.objects.filter(item_name='').exists())

    # def test_import_for_multiple_users(self):
    #     # Create another user and test importing data as the logged-in user
    #     another_user = User.objects.create_user(username='user2', password='password2')
    #     csv_file = self.generate_csv_file([
    #         ['Test List', 'Sample Item', 'Sample Text', 'True', '2024-10-01', '2024-12-01']
    #     ])
    #     response = self.client.post(self.url, {'csv_file': csv_file})
    #     self.assertRedirects(response, reverse('todo:index'))
    #     self.assertEqual(List.objects.filter(title_text='Test List', listitem__item_name='Sample Item').count(), 1)
