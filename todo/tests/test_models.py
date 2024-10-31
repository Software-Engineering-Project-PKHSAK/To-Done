from django.test import TestCase
from django.contrib.auth.models import User
from .models import List, ListTags, ListItem, Template, TemplateItem, SharedUsers, SharedList
from django.utils import timezone
from datetime import timedelta

class TodoModelTests(TestCase):
    def setUp(self):
        # Create a user for testing
        self.user = User.objects.create(username='testuser')

    def test_create_list(self):
        """Test creating a List object"""
        list_instance = List.objects.create(
            title_text="Shopping List",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            list_tag="groceries",
            user_id=self.user,
            is_shared=False
        )
        self.assertEqual(str(list_instance), "Shopping List")
        self.assertEqual(list_instance.list_tag, "groceries")

    def test_create_list_tag(self):
        """Test creating a ListTags object"""
        list_tag_instance = ListTags.objects.create(
            user_id=self.user,
            tag_name="Important",
            created_on=timezone.now()
        )
        self.assertEqual(str(list_tag_instance), "Important")

    def test_create_list_item(self):
        """Test creating a ListItem and associating with List"""
        list_instance = List.objects.create(
            title_text="Work Tasks",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id=self.user
        )
        list_item_instance = ListItem.objects.create(
            item_name="Finish Report",
            item_text="Complete the quarterly report",
            is_done=False,
            created_on=timezone.now(),
            list=list_instance,
            finished_on=timezone.now() + timedelta(days=1),
            due_date=timezone.now().date() + timedelta(days=2),
            tag_color="blue"
        )
        self.assertEqual(str(list_item_instance), "Complete the quarterly report: False")
        self.assertFalse(list_item_instance.is_done)

    def test_update_list_item_status(self):
        """Test updating the status of a ListItem"""
        list_instance = List.objects.create(
            title_text="Daily Chores",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id=self.user
        )
        list_item_instance = ListItem.objects.create(
            item_text="Clean kitchen",
            created_on=timezone.now(),
            list=list_instance,
            finished_on=timezone.now(),
            due_date=timezone.now().date(),
            tag_color="green"
        )
        list_item_instance.is_done = True
        list_item_instance.save()
        self.assertTrue(list_item_instance.is_done)

    def test_create_template(self):
        """Test creating a Template object"""
        template_instance = Template.objects.create(
            title_text="Weekly Review Template",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id=self.user
        )
        self.assertEqual(str(template_instance), "Weekly Review Template")

    def test_create_template_item(self):
        """Test creating a TemplateItem and associating with Template"""
        template_instance = Template.objects.create(
            title_text="Personal Development",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id=self.user
        )
        template_item_instance = TemplateItem.objects.create(
            item_text="Read a new book",
            created_on=timezone.now(),
            template=template_instance,
            finished_on=timezone.now() + timedelta(days=7),
            due_date=timezone.now().date() + timedelta(days=10),
            tag_color="yellow"
        )
        self.assertEqual(str(template_item_instance), "Read a new book")
        self.assertEqual(template_item_instance.tag_color, "yellow")

    def test_create_shared_user(self):
        """Test creating a SharedUsers entry"""
        list_instance = List.objects.create(
            title_text="Project Tasks",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id=self.user
        )
        shared_user_instance = SharedUsers.objects.create(
            list_id=list_instance,
            shared_user="collaborator@example.com"
        )
        self.assertEqual(str(shared_user_instance), str(list_instance.id))
        self.assertEqual(shared_user_instance.shared_user, "collaborator@example.com")

    def test_create_shared_list(self):
        """Test creating a SharedList entry"""
        shared_list_instance = SharedList.objects.create(
            user=self.user,
            shared_list_id="12345"
        )
        self.assertEqual(str(shared_list_instance), str(self.user))
        self.assertEqual(shared_list_instance.shared_list_id, "12345")

    def test_list_default_tag(self):
        """Test that List objects default to 'none' for list_tag"""
        list_instance = List.objects.create(
            title_text="Misc Tasks",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id=self.user
        )
        self.assertEqual(list_instance.list_tag, "none")

    def test_str_methods(self):
        """Test the __str__ methods for each model"""
        list_instance = List.objects.create(
            title_text="Test List",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id=self.user
        )
        list_tag_instance = ListTags.objects.create(
            user_id=self.user,
            tag_name="Test Tag",
            created_on=timezone.now()
        )
        list_item_instance = ListItem.objects.create(
            item_text="Test Item",
            created_on=timezone.now(),
            list=list_instance,
            finished_on=timezone.now(),
            due_date=timezone.now().date(),
            tag_color="blue"
        )
        self.assertEqual(str(list_instance), "Test List")
        self.assertEqual(str(list_tag_instance), "Test Tag")
        self.assertEqual(str(list_item_instance), "Test Item: False")
