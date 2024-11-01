# MIT License

# Copyright © 2024 Akarsh Reddy Eathamukkala

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the “Software”), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to
# do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from django.urls import reverse
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from todo.views import config, config_hook, delete_template, login_request, template_from_todo, template, delete_todo, index, getListTagsByUserid, removeListItem, addNewListItem, updateListItem, createNewTodoList, register_request, getListItemByName, getListItemById, markListItem, todo_from_template
from django.utils import timezone
from todo.models import List, ListItem, Template, TemplateItem, ListTags, SharedList
from todo.forms import NewUserForm
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.messages import get_messages

import json


class TestViews(TestCase):
    def setUp(self):
        # Every test needs access to the client and request factory.
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='jacob', email='jacob@…', password='top_secret')
        self.anonymous_user = AnonymousUser()
        # Config setup
        config["darkMode"] = False
        config["primary_color"] = '#0fa662'
        config["hover_color"] = "#0b8f54"

    def testLogin(self):
        request = self.factory.get('/login/')
        request.user = self.user
        post = request.POST.copy()  # to make it mutable
        post['todo'] = 1
        print(request)
        request.POST = post
        response = login_request(request)
        self.assertEqual(response.status_code, 200)

    def testLogin_with_invalid_credentials(self):
        response = self.client.post(reverse('todo:login'), {
            'username': 'wronguser',
            'password': 'wrongpassword'
        })

        # Check that the response is rendered to the correct template
        self.assertTemplateUsed(response, 'todo/login.html')

        # # Check that the form contains errors
        form = response.context['login_form']
        self.assertIsInstance(form, AuthenticationForm)

        # Check that the error message is set
        messages_list = list(response.wsgi_request._messages)
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Invalid username or password.")
        
        # Ensure the user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def testLogin_with_invalid_form(self):
        response = self.client.post(reverse('todo:login'), {
            'username': '',  # Invalid: empty username
            'password': ''   # Invalid: empty password
        })

        # Check that the response is rendered to the correct template
        self.assertTemplateUsed(response, 'todo/login.html')

        # Check that the form is instantiated correctly
        form = response.context['login_form']
        self.assertIsInstance(form, AuthenticationForm)

        # Check that the form contains errors
        self.assertFalse(form.is_valid())  # The form should have errors

        # Ensure error messages are displayed
        messages_list = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages_list), 0)  # Ensure there is at least one message
        self.assertIn("Invalid", str(messages_list[0]))  # Check for required field error

        # Ensure the user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        # Test specific form errors (if you want to check individual fields)
        self.assertIn('username', str(messages_list[0]))  # Ensure 'username' field has errors
        self.assertIn('password', str(messages_list[0]))  # Ensure 'password' field has errors

    def testSavingTodoList(self):
        response = self.client.get(reverse('todo:createNewTodoList'))
        self.assertEqual(response.status_code, 302)
        # print(response)

    def test_delete_todo_list(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        todo = List.objects.create(
            title_text="test list",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=self.user.id,
        )
        ListItem.objects.create(
            item_name="test item",
            item_text="This is a test item on a test list",
            created_on=timezone.now(),
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now(),
            list=todo,
            is_done=False,
        )
        post = request.POST.copy()
        post['todo'] = 1
        request.POST = post
        response = delete_todo(request)
        self.assertEqual(response.status_code, 302)

    def test_delete_todo_list_not_logged_in(self):
        request = self.factory.get('/todo/')
        request.user = self.anonymous_user
        post = request.POST.copy()
        post['todo'] = 1
        request.POST = post
        response = delete_todo(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:login'))

    def test_getListTagsByUserid(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        ListTags.objects.create(
            user_id_id=self.user.id,
            tag_name='test',
            created_on=timezone.now()
        )
        post = request.POST.copy()
        post['todo'] = 1
        request.POST = post
        request.method = "POST"
        response = getListTagsByUserid(request)
        print('response:')
        print(response)
        self.assertIsNotNone(response)

    def test_getListTagsByUserid_not_logged_in(self):
        request = self.factory.get('/todo/')
        request.user = self.anonymous_user
        post = request.POST.copy()
        post['todo'] = 1
        request.POST = post
        request.method = "POST"
        response = getListTagsByUserid(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:login'))
    
    def test_index(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        response = index(request)
        self.assertEqual(response.status_code, 200)
    
    def test_index_not_logged_in(self):
        request = self.factory.get('/todo/')
        request.user = self.anonymous_user
        response = index(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:login'))

    def test_template_from_todo_redirect(self):
        client = self.client
        response = client.get(reverse('todo:template_from_todo'))
        self.assertEquals(response.status_code, 302)

    def test_template_from_todo_function(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        todo = List.objects.create(
            title_text="test list",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=request.user.id,
        )
        item = ListItem.objects.create(
            item_name="test item",
            item_text="This is a test item on a test list",
            created_on=timezone.now(),
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now(),
            list=todo,
            is_done=True,
        )
        post = request.POST.copy()  # to make it mutable
        post['todo'] = 1
        request.POST = post
        response = template_from_todo(request)
        self.assertEqual(response.status_code, 302)
    
    def test_template_from_todo_function_not_logged_in(self):
        request = self.factory.get('/todo/')
        request.user = self.anonymous_user
        post = request.POST.copy()  # to make it mutable
        post['todo'] = 1
        request.POST = post
        response = template_from_todo(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:login'))

    def test_template_display(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        new_template = Template.objects.create(
            title_text="test template",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=request.user.id
        )
        template_item = TemplateItem.objects.create(
            item_text="test item",
            created_on=timezone.now(),
            template=new_template,
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now()
        )
        post = request.POST.copy()  # to make it mutable
        post['todo'] = 1
        request.POST = post
        response = template(request, 1)
        self.assertEqual(response.status_code, 200)
    
    def test_template_display_not_logged_in(self):
        request = self.factory.get('/todo/')
        request.user = self.anonymous_user
        post = request.POST.copy()  # to make it mutable
        post['todo'] = 1
        request.POST = post
        response = template(request, 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:login'))
        
    def test_removeListItem(self):
        request = self.factory.get('/todo/')
        request.user = self.user

        todo = List.objects.create(
            title_text="test list",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=self.user.id,
        )

        ListItem.objects.create(
            item_name="test item",
            item_text="This is a test item on a test list",
            created_on=timezone.now(),
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now(),
            list=todo,
            is_done=False,
        )

        post = request.POST.copy()
        # post['list_item_id'] = 1
        request.method = "POST"
        request._body = json.dumps({"list_item_id": 1}).encode('utf-8')
        response = removeListItem(request)
        print(response)
        self.assertIsNotNone(response)

    def test_NewUserForm(self):
        form_data = {'email': '123@123.com', 'username': '123',
                     'password1': 'K!35EGL&g7#U', 'password2': 'K!35EGL&g7#U'}
        form = NewUserForm(form_data)
        self.assertTrue(form.is_valid())

    def test_addNewListItem(self):

        todo = List.objects.create(
            title_text="test list",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=self.user.id,
        )

        params = {
            'list_id': todo.id,
            'list_item_name': "random",
            "create_on": 1670292391,
            "due_date": "2023-01-01",
            "tag_color": "#f9f9f9",
            "item_text": "",
            "is_done": False
        }

        request = self.factory.post(f'/todo/', data=params,
                                    content_type="application/json")
        request.user = self.user
        # request.method = "POST"
        print(type(params))
        # param = json.dumps(param,cls=DateTimeEncoder)
        # request._body = json.dumps(params, separators=(',', ':')).encode('utf-8')
        temp = addNewListItem(request)
        response = index(request)
        self.assertEqual(response.status_code, 200)

    def test_updateListItem(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        todo = List.objects.create(
            title_text="test list 2",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=request.user.id,
        )
        item = ListItem.objects.create(
            item_name="test item 2",
            item_text="This is a test item on a test list",
            created_on=timezone.now(),
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now(),
            list=todo,
            is_done=False,
        )
        post = request.POST.copy()
        post['todo'] = 1
        post['note'] = 'test note'
        request.POST = post
        request.method = "POST"
        response = updateListItem(request, item.id)
        self.assertEqual(response.status_code, 302)

    def test_createNewTodoList(self):
        test_data = {'list_name': 'test',
                     'create_on': 1670292391,
                     'list_tag': 'test_tag',
                     'shared_user': None,
                     'create_new_tag': True}
        request = self.factory.post(f'/todo/', data=test_data,
                                    content_type="application/json")
        request.user = self.user
        temp = createNewTodoList(request)
        response = index(request)
        self.assertEqual(response.status_code, 200)

    def test_getListItemByName(self):
        todo = List.objects.create(
            title_text="test list",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=self.user.id,
        )
        ListItem.objects.create(
            item_name="test item",
            item_text="This is a test item on a test list",
            created_on=timezone.now(),
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now(),
            list=todo,
            is_done=False,
        )
        test_data = {'list_id': '1',
                     'list_item_name': "test item"
                     }
        request = self.factory.post(f'/todo/', data=test_data,
                                    content_type="application/json")
        request.user = self.user
        response = getListItemByName(request)
        self.assertEqual(response.status_code, 200)

    def test_getListItemById(self):
        todo = List.objects.create(
            title_text="test list 3",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=self.user.id,
        )
        item = ListItem.objects.create(
            item_name="test item 3",
            item_text="This is a test item on a test list",
            created_on=timezone.now(),
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now(),
            list=todo,
            is_done=False,
        )
        test_data = {'list_id': str(todo.id),
                     'list_item_name': 'test item 3',
                     'list_item_id': str(item.id)
                     }
        request = self.factory.post(f'/todo/', data=test_data,
                                    content_type="application/json")
        request.user = self.user
        temp = getListItemById(request)
        response = index(request)
        self.assertEqual(response.status_code, 200)

    def test_markListItem(self):
        todo = List.objects.create(
            title_text="test list",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=self.user.id,
        )

        listItem = ListItem.objects.create(
            item_name="test item",
            item_text="This is a test item on a test list",
            created_on=timezone.now(),
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now(),
            list=todo,
            is_done=False,
        )

        params = {
            'list_id': todo.id,
            'list_item_name': listItem.item_name,
            "create_on": 1670292391,
            "due_date": "2023-01-01",
            "finish_on": 1670292392,
            "is_done": True,
            "list_item_id": listItem.id,
        }

        request = self.factory.post(f'/todo/', data=params,
                                    content_type="application/json")
        request.user = self.user
        temp = markListItem(request)
        response = index(request)
        self.assertEqual(response.status_code, 200)

    def test_createNewTodoList2(self):
        test_data = {'list_name': 'test',
                     'create_on': 1670292391,
                     'list_tag': 'test_tag',
                     'shared_user': 'someone',
                     'create_new_tag': True}
        request = self.factory.post(f'/todo/', data=test_data,
                                    content_type="application/json")
        request.user = self.user
        temp = createNewTodoList(request)
        response = index(request)
        self.assertEqual(response.status_code, 200)

    def test_createNewTodoList3(self):
        sharedUser = User.objects.create_user(
            username='share', email='share@…', password='top_secret')
        sharedList = SharedList.objects.create(
            user=sharedUser,
            shared_list_id=""
        )

        test_data = {'list_name': 'test',
                     'create_on': 1670292391,
                     'list_tag': 'test_tag',
                     'shared_user': 'share',
                     'create_new_tag': True}
        request = self.factory.post(f'/todo/', data=test_data,
                                    content_type="application/json")
        request.user = self.user
        temp = createNewTodoList(request)
        response = index(request)
        self.assertEqual(response.status_code, 200)

    def test_todo_from_template(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        new_template = Template.objects.create(
            title_text="test template",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=request.user.id
        )
        template_item = TemplateItem.objects.create(
            item_text="test item",
            created_on=timezone.now(),
            template=new_template,
            finished_on=timezone.now(),
            tag_color="#f9f9f9",
            due_date=timezone.now()
        )

        post = request.POST.copy()
        post['todo'] = 1
        post['template'] = new_template.id
        request.POST = post
        request.method = "POST"
        response = todo_from_template(request)
        self.assertEqual(response.status_code, 302)

    def test_login_request(self):
        test_data = {'username': 'jacob',
                     'password': 'top_secret'}
        request = self.factory.post(f'/login/', data=test_data,
                                    content_type="application/json")
        request.user = self.user
        setattr(request, 'session', 'session')
        setattr(request, '_messages', FallbackStorage(request))
        response = login_request(request)
        self.assertEqual(response.status_code, 200)

    def test_delete_template(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        new_template = Template.objects.create(
            title_text="test template",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=request.user.id
        )
        post = request.POST.copy()
        post['todo'] = 1
        request.POST = post
        request.method = "POST"
        response = delete_template(request, new_template.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/templates')

    def test_delete_template_not_logged_in(self):
        request = self.factory.get('/todo/')
        request.user = self.anonymous_user
        new_template = Template.objects.create(
            title_text="test template",
            created_on=timezone.now(),
            updated_on=timezone.now(),
            user_id_id=request.user.id
        )
        post = request.POST.copy()
        post['todo'] = 1
        request.POST = post
        request.method = "POST"
        response = delete_template(request, new_template.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login')

    def test_delete_template_undefined(self):
        request = self.factory.get('/todo/')
        request.user = self.anonymous_user
        request.method = "POST"
        response = delete_template(request, 9999)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login')

    def test_delete_template_undefined_logged_in(self):
        request = self.factory.get('/todo/')
        request.user = self.user
        request.method = "POST"
        response = delete_template(request, 9999)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/templates')
  
    def test_initial_config_state(self):
        # Initial config state check
        self.assertFalse(config["darkMode"])
        self.assertEqual(config["primary_color"], '#0fa662')
        self.assertEqual(config["hover_color"], '#0b8f54')

    def test_config_change_index(self): 
        # Call config_hook and check if it toggles to dark mode on index page
        request = self.factory.get('/todo/')
        request.user = self.user
        request.method = "POST"
        response = config_hook(request, 'index')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:index'))
        self.assertTrue(config["darkMode"])
        self.assertEqual(config["primary_color"], '#000000')
        self.assertEqual(config["hover_color"], '#cccccc')

        # Call config_hook again and check if it toggles back to light mode
        response = config_hook(request, 'index')
        
        # Check config changes for dark mode disabled
        self.assertFalse(config["darkMode"])
        self.assertEqual(config["primary_color"], '#0fa662')
        self.assertEqual(config["hover_color"], '#0b8f54')

        # Verify redirect URL again
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:index'))

    def test_config_change_login(self): 
        # Call config_hook and check if it toggles to dark mode on login page
        request = self.factory.get('/todo/')
        request.user = self.user
        request.method = "POST"
        response = config_hook(request, 'login')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:login'))
        self.assertTrue(config["darkMode"])
        self.assertEqual(config["primary_color"], '#000000')
        self.assertEqual(config["hover_color"], '#cccccc')

        # Call config_hook again and check if it toggles back to light mode
        response = config_hook(request, 'login')
        
        # Check config changes for dark mode disabled
        self.assertFalse(config["darkMode"])
        self.assertEqual(config["primary_color"], '#0fa662')
        self.assertEqual(config["hover_color"], '#0b8f54')

        # Verify redirect URL again
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:login'))

    def test_config_change_template(self): 
        # Call config_hook and check if it toggles to dark mode on template page
        request = self.factory.get('/todo/')
        request.user = self.user
        request.method = "POST"
        response = config_hook(request, 'template')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:template'))
        self.assertTrue(config["darkMode"])
        self.assertEqual(config["primary_color"], '#000000')
        self.assertEqual(config["hover_color"], '#cccccc')

        # Call config_hook again and check if it toggles back to light mode
        response = config_hook(request, 'template')
        
        # Check config changes for dark mode disabled
        self.assertFalse(config["darkMode"])
        self.assertEqual(config["primary_color"], '#0fa662')
        self.assertEqual(config["hover_color"], '#0b8f54')

        # Verify redirect URL again
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('todo:template'))