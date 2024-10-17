import datetime
import json

from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.http import HttpResponse, JsonResponse, Http404, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.views.decorators.http import require_POST

from todo.models import List, ListItem, Template, TemplateItem, ListTags, SharedUsers, SharedList

from todo.forms import NewUserForm
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.core.mail import EmailMessage
from google.oauth2 import id_token
from google.auth.transport import requests

config = {
    "darkMode": False,
    "primary_color": '#0fa662',
    "hover_color": "#0b8f54"
}

def config_hook(request, template_str):
    config["darkMode"] = not config["darkMode"]
    if config["darkMode"]:
        config["primary_color"] = '#000000'
        config["hover_color"] = '#cccccc'
    else:
        config["primary_color"] = '#0fa662'
        config["hover_color"] = '#0b8f54'
    return redirect('todo:' + template_str)

# Render the home page with users' to-do lists
def index(request, list_id=0):
    """
    Renders the index page for the to-do application.

    This view function retrieves the user's lists and items based on their authentication status
    and whether a specific list ID is provided. If the user is not authenticated, they are redirected
    to the login page. If a valid list ID is provided, that specific list is retrieved; otherwise, the
    latest lists for the authenticated user are fetched along with any shared lists. It also gathers
    the user's list items, saved templates, and list tags, and checks for overdue items to change their color.

    Args:
        request: The HTTP request object.
        list_id (int, optional): The ID of the specific list to display. Defaults to 0.

    Returns:
        HttpResponse: The rendered HTML response for the index page with the context containing:
            - latest_lists: A list of the user's latest lists or the specific list if an ID is provided.
            - latest_list_items: A queryset of all list items ordered by their list ID.
            - templates: A queryset of saved templates for the authenticated user, ordered by creation date.
            - list_tags: A queryset of tags associated with the user's lists, ordered by creation date.
            - shared_list: A list of shared lists for the user.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    
    shared_list = []

    if list_id != 0:
        # latest_lists = List.objects.filter(id=list_id, user_id_id=request.user.id)
        latest_lists = List.objects.filter(id=list_id)

    else:
        latest_lists = List.objects.filter(user_id_id=request.user.id).order_by('-updated_on')

        try:
            query_list_str = SharedList.objects.get(user_id=request.user.id).shared_list_id
        except SharedList.DoesNotExist:
            query_list_str = None
        
        if query_list_str != None:
            shared_list_id = query_list_str.split(" ")
            shared_list_id.remove("")

            latest_lists = list(latest_lists)

            for list_id in shared_list_id:
            
                try:
                    query_list = List.objects.get(id=int(list_id))
                except List.DoesNotExist:
                    query_list = None

                if query_list:
                    shared_list.append(query_list)
        
    latest_list_items = ListItem.objects.order_by('list_id')
    saved_templates = Template.objects.filter(user_id_id=request.user.id).order_by('created_on')
    list_tags = ListTags.objects.filter(user_id=request.user.id).order_by('created_on')
    
    # change color when is or over due
    cur_date = datetime.date.today()
    for list_item in latest_list_items:       
        list_item.color = "#FF0000" if cur_date > list_item.due_date else "#000000"
            
    context = {
        'latest_lists': latest_lists,
        'latest_list_items': latest_list_items,
        'templates': saved_templates,
        'list_tags': list_tags,
        'shared_list': shared_list,
        'config': config
    }
    return render(request, 'todo/index.html', context)

# Create a new to-do list from templates and redirect to the to-do list homepage
def todo_from_template(request):
    """
    Creates a new to-do list from a selected template.

    This view function is invoked when a user wants to create a new to-do list based on an existing template.
    It first checks if the user is authenticated. If not, it redirects them to the login page. If the user
    is authenticated, it fetches the specified template, creates a new to-do list with the template's title,
    and then populates the new list with items defined in the template.

    Args:
        request: The HTTP request object containing the user's input data.

    Returns:
        HttpResponse: A redirect to the to-do page after successfully creating the new list and its items.

    Raises:
        Http404: If the specified template does not exist, a 404 error is raised.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    template_id = request.POST['template']
    fetched_template = get_object_or_404(Template, pk=template_id)
    todo = List.objects.create(
        title_text=fetched_template.title_text,
        created_on=timezone.now(),
        updated_on=timezone.now(),
        user_id_id=request.user.id
    )
    for template_item in fetched_template.templateitem_set.all():
        ListItem.objects.create(
            item_name=template_item.item_text,
            item_text="",
            created_on=timezone.now(),
            finished_on=timezone.now(),
            due_date=timezone.now(),
            tag_color=template_item.tag_color,
            list=todo,
            is_done=False,
        )
    return redirect("/todo")


# Create a new Template from existing to-do list and redirect to the templates list page
def template_from_todo(request):
    """
    Creates a new template from a selected to-do list.

    This view function is invoked when a user wants to create a new template based on an existing to-do list.
    It first checks if the user is authenticated; if not, it redirects them to the login page. If the user
    is authenticated, it fetches the specified to-do list, creates a new template with the to-do list's title,
    and then populates the new template with items defined in the to-do list.

    Args:
        request: The HTTP request object containing the user's input data.

    Returns:
        HttpResponse: A redirect to the templates page after successfully creating the new template and its items.

    Raises:
        Http404: If the specified to-do list does not exist, a 404 error is raised.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    todo_id = request.POST['todo']
    fetched_todo = get_object_or_404(List, pk=todo_id)
    new_template = Template.objects.create(
        title_text=fetched_todo.title_text,
        created_on=timezone.now(),
        updated_on=timezone.now(),
        user_id_id=request.user.id
    )
    for todo_item in fetched_todo.listitem_set.all():
        TemplateItem.objects.create(
            item_text=todo_item.item_name,
            created_on=timezone.now(),
            finished_on=timezone.now(),
            due_date=timezone.now(),
            tag_color = todo_item.tag_color,
            template=new_template
        )
    return redirect("/templates")


# Delete a to-do list
def delete_todo(request):
    """
    Deletes a specified to-do item.

    This view function is invoked when a user wants to delete a to-do item. 
    It first checks if the user is authenticated; if not, it redirects them to the login page. 
    If the user is authenticated, it retrieves the specified to-do item by its ID and deletes it.

    Args:
        request: The HTTP request object containing the user's input data.

    Returns:
        HttpResponse: A redirect to the to-do page after successfully deleting the specified to-do item.

    Raises:
        Http404: If the specified to-do item does not exist, a 404 error is raised.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    todo_id = request.POST['todo']
    fetched_todo = get_object_or_404(List, pk=todo_id)
    fetched_todo.delete()
    return redirect("/todo")


# Render the template list page
def template(request, template_id=0):
    """
    Retrieves and displays saved templates for the authenticated user.

    This view function is invoked to render a list of saved templates. It first checks if the user is 
    authenticated; if not, it redirects them to the login page. If a template ID is provided, it fetches
    that specific template; otherwise, it retrieves all templates created by the authenticated user,
    ordered by creation date.

    Args:
        request: The HTTP request object containing the user's input data.
        template_id (int, optional): The ID of the template to retrieve. Defaults to 0.

    Returns:
        HttpResponse: Renders the template page with the list of saved templates.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    if template_id != 0:
        saved_templates = Template.objects.filter(id=template_id)
    else:
        saved_templates = Template.objects.filter(user_id_id=request.user.id).order_by('created_on')
    context = {
        'templates': saved_templates,
        'config': config
    }
    return render(request, 'todo/template.html', context)


# Remove a to-do list item, called by javascript function
@csrf_exempt
def removeListItem(request):
    """
    Removes a to-do list item based on the provided list item ID.

    This view function is invoked via a JavaScript call to remove a specified item from a to-do list. 
    It checks if the user is authenticated; if not, it redirects them to the login page. Upon receiving a 
    POST request, it decodes the JSON body to retrieve the list item ID and attempts to delete the corresponding 
    ListItem from the database. If an integrity error occurs during the deletion, it logs the error message.

    Args:
        request: The HTTP request object containing the user's input data.

    Returns:
        HttpResponse: A redirect to the to-do page after successfully removing the specified list item.
    
    Raises:
        IntegrityError: If there is a database integrity error while trying to delete the list item.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        list_item_id = body['list_item_id']
        print("list_item_id: ", list_item_id)
        try:
            with transaction.atomic():
                being_removed_item = ListItem.objects.get(id=list_item_id)
                being_removed_item.delete()
        except IntegrityError as e:
            print(str(e))
            print("unknown error occurs when trying to update todo list item text")
        return redirect("/todo")
    else:
        return redirect("/todo")

# Update a to-do list item, called by javascript function
@csrf_exempt
def updateListItem(request, item_id):
    """
    Updates the text of a to-do list item based on the provided item ID.

    This view function is called to update the text of a specific to-do list item. It checks if the user 
    is authenticated; if not, it redirects them to the login page. If the request method is POST, it retrieves
    the updated text from the request, fetches the ListItem by ID, and updates its text. If the item ID is 
    invalid (less than or equal to zero), it redirects to the index page. An IntegrityError during the 
    transaction is caught and logged.

    Args:
        request: The HTTP request object containing the user's input data.
        item_id (int): The ID of the to-do list item to be updated.

    Returns:
        HttpResponse: Redirects to the home page after updating the item or to the index if item ID is invalid.
    
    Raises:
        IntegrityError: If there is a database integrity error while trying to update the list item.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    if request.method == 'POST':
        updated_text = request.POST['note']
        # print(request.POST)
        print(updated_text)
        print(item_id)
        if item_id <= 0:
            return redirect("index")
        try:
            with transaction.atomic():
                todo_list_item = ListItem.objects.get(id=item_id)
                todo_list_item.item_text = updated_text
                todo_list_item.save(force_update=True)
        except IntegrityError as e:
            print(str(e))
            print("unknown error occurs when trying to update todo list item text")
        return redirect("/")
    else:
        return redirect("index")


# Add a new to-do list item, called by javascript function
@csrf_exempt
def addNewListItem(request):
    """
    Adds a new to-do list item based on the provided data.

    This view function is invoked to create a new to-do list item. It checks if the user is authenticated;
    if not, it redirects them to the login page. On receiving a POST request, it decodes the JSON body to 
    retrieve the list item details and creates a new ListItem object. If an IntegrityError occurs during 
    the creation process, it logs the error and returns an item ID of -1.

    Args:
        request: The HTTP request object containing the user's input data.

    Returns:
        JsonResponse: Contains the ID of the newly created item or -1 in case of failure.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        list_id = body['list_id']
        item_name = body['list_item_name']
        create_on = body['create_on']
        create_on_time = datetime.datetime.fromtimestamp(create_on)
        finished_on_time = datetime.datetime.fromtimestamp(create_on)
        due_date = body['due_date']
        tag_color = body['tag_color']
        print(item_name)
        print(create_on)
        result_item_id = -1
        # create a new to-do list object and save it to the database
        try:
            with transaction.atomic():
                todo_list_item = ListItem(item_name=item_name, created_on=create_on_time, finished_on=finished_on_time, due_date=due_date, tag_color=tag_color, list_id=list_id, item_text="", is_done=False)
                todo_list_item.save()
                result_item_id = todo_list_item.id
        except IntegrityError:
            print("unknown error occurs when trying to create and save a new todo list")
            return JsonResponse({'item_id': -1})
        return JsonResponse({'item_id': result_item_id})  # Sending an success response
    else:
        return JsonResponse({'item_id': -1})


# Mark a to-do list item as done/not done, called by javascript function
@csrf_exempt
def markListItem(request):
    """
    Marks a to-do list item as done or undoes the action based on the provided data.

    This view function is called to toggle the completion status of a specific list item. It checks if the 
    user is authenticated; if not, it redirects them to the login page. Upon receiving a POST request, it 
    decodes the JSON body to get the relevant details, including the item ID and completion status. It updates 
    the ListItem's is_done field and the finished_on timestamp. If an IntegrityError occurs during the 
    transaction, it logs the error and returns an empty JsonResponse.

    Args:
        request: The HTTP request object containing the user's input data.

    Returns:
        JsonResponse: Contains the name of the item and the list if successful, or an empty response in case of failure.
    
    Raises:
        IntegrityError: If there is a database integrity error while trying to update the list item.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        list_id = body['list_id']
        list_item_name = body['list_item_name']
        list_item_id = body['list_item_id']
        # remove the first " and last "
        list_item_is_done = True
        is_done_str = str(body['is_done'])
        finish_on = body['finish_on']
        finished_on_time = datetime.datetime.fromtimestamp(finish_on)
        print("is_done: " + str(body['is_done']))
        if is_done_str == "0" or is_done_str == "False" or is_done_str == "false":
            list_item_is_done = False
        try:
            with transaction.atomic():
                query_list = List.objects.get(id=list_id)
                query_item = ListItem.objects.get(id=list_item_id)
                query_item.is_done = list_item_is_done
                query_item.finished_on = finished_on_time
                query_item.save()
                # Sending an success response
                return JsonResponse({'item_name': query_item.item_name, 'list_name': query_list.title_text, 'item_text': query_item.item_text})
        except IntegrityError:
            print("query list item" + str(list_item_name) + " failed!")
            JsonResponse({})
        return HttpResponse("Success!")  # Sending an success response
    else:
        return HttpResponse("Request method is not a Post")

# Get all the list tags by user id
@csrf_exempt
def getListTagsByUserid(request):
    """
    Retrieves all list tags associated with the authenticated user.

    This view function is called to fetch the list tags created by the authenticated user. It checks 
    if the user is authenticated; if not, it redirects them to the login page. Upon receiving a POST 
    request, it retrieves the user's tags from the database and returns them as a JSON response. 
    If an IntegrityError occurs during the transaction, it logs the error and returns an empty JsonResponse.

    Args:
        request: The HTTP request object containing the user's input data.

    Returns:
        JsonResponse: Contains the list of tags associated with the user or an empty response in case of failure.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user_id = request.user.id
                list_tag_list = ListTags.objects.filter(user_id=user_id).values()
                return JsonResponse({'list_tag_list': list(list_tag_list)})
        except IntegrityError:
            print("query list tag by user_id = " + str(user_id) + " failed!")
            JsonResponse({})
    else:
        return JsonResponse({'result': 'get'})  # Sending an success response

# Get a to-do list item by name, called by javascript function
@csrf_exempt
def getListItemByName(request):
    """
    Retrieve a to-do list item by its name.

    This function checks if the user is authenticated, and if so, 
    it processes a POST request to get the item details based on 
    the provided list ID and item name. 

    Args:
        request (HttpRequest): The HTTP request object containing 
                               the user's request data.

    Returns:
        JsonResponse: A JSON response containing the item ID, item 
                      name, list name, and item text if successful, 
                      or a JSON response indicating a failure.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        list_id = body['list_id']
        list_item_name = body['list_item_name']
        # remove the first " and last "
        # list_item_name = list_item_name

        print("list_id: " + list_id)
        print("list_item_name: " + list_item_name)
        try:
            with transaction.atomic():
                query_list = List.objects.get(id=list_id)
                query_item = ListItem.objects.get(list_id=list_id, item_name=list_item_name)
                # Sending an success response
                return JsonResponse({'item_id': query_item.id, 'item_name': query_item.item_name, 'list_name': query_list.title_text, 'item_text': query_item.item_text})
        except IntegrityError:
            print("query list item" + str(list_item_name) + " failed!")
            JsonResponse({})
    else:
        return JsonResponse({'result': 'get'})  # Sending an success response


# Get a to-do list item by id, called by javascript function
@csrf_exempt
def getListItemById(request):
    """
    Retrieve a to-do list item by its ID.

    This function checks if the user is authenticated and processes 
    a POST request to retrieve the details of a specific item 
    identified by its ID.

    Args:
        request (HttpRequest): The HTTP request object containing 
                               the user's request data.

    Returns:
        JsonResponse: A JSON response containing the item ID, item 
                      name, list name, and item text if successful, 
                      or a JSON response indicating a failure.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        list_id = body['list_id']
        list_item_name = body['list_item_name']
        list_item_id = body['list_item_id']

        print("list_id: " + list_id)
        print("list_item_name: " + list_item_name)
        print("list_item_id: " + list_item_id)

        try:
            with transaction.atomic():
                query_list = List.objects.get(id=list_id)
                query_item = ListItem.objects.get(id=list_item_id)
                print("item_text", query_item.item_text)
                # Sending an success response
                return JsonResponse({'item_id': query_item.id, 'item_name': query_item.item_name, 'list_name': query_list.title_text, 'item_text': query_item.item_text})
        except IntegrityError:
            print("query list item" + str(list_item_name) + " failed!")
            JsonResponse({})
    else:
        return JsonResponse({'result': 'get'})  # Sending an success response


# Create a new to-do list, called by javascript function
@csrf_exempt
def createNewTodoList(request):
    """
    Create a new to-do list.

    This function checks if the user is authenticated and processes 
    a POST request to create a new to-do list with the specified 
    attributes, including sharing it with other users if needed.

    Args:
        request (HttpRequest): The HTTP request object containing 
                               the user's request data.

    Returns:
        HttpResponse: A success response if the list is created 
                      successfully, or an error message if the 
                      request fails or the user is not authenticated.
    """
    if not request.user.is_authenticated:
        return redirect("/login")

    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        list_name = body['list_name']
        create_on = body['create_on']
        tag_name = body['list_tag']
        shared_user = body['shared_user']
        user_not_found = []
        print(shared_user)
        create_on_time = datetime.datetime.fromtimestamp(create_on)
        # print(list_name)
        # print(create_on)
        # create a new to-do list object and save it to the database
        try:
            with transaction.atomic():
                user_id = request.user.id
                # print(user_id)
                todo_list = List(user_id_id=user_id, title_text=list_name, created_on=create_on_time, updated_on=create_on_time, list_tag=tag_name)
                if body['create_new_tag']:
                    # print('new tag')
                    new_tag = ListTags(user_id_id=user_id, tag_name=tag_name, created_on=create_on_time)
                    new_tag.save()

                todo_list.save()
                print(todo_list.id)

                # Progress
                if body['shared_user']:
                    user_list = shared_user.split(' ')
                    

                    k = len(user_list)-1
                    i = 0
                    while i <= k:

                        try:
                            query_user = User.objects.get(username=user_list[i])
                        except User.DoesNotExist:
                            query_user = None

                        if query_user:

                            shared_list_id = SharedList.objects.get(user=query_user).shared_list_id
                            shared_list_id = shared_list_id + str(todo_list.id) + " "
                            SharedList.objects.filter(user=query_user).update(shared_list_id=shared_list_id)
                            i += 1
                            
                        else:
                            print("No user named " + user_list[i] + " found!")
                            user_not_found.append(user_list[i])
                            user_list.remove(user_list[i])
                            k -= 1

                    shared_user = ' '.join(user_list)
                    new_shared_user = SharedUsers(list_id=todo_list, shared_user=shared_user)
                    new_shared_user.save()

                    print(user_not_found)

                    if user_list:
                        List.objects.filter(id=todo_list.id).update(is_shared=True)

        except IntegrityError as e:
            print(str(e))
            print("unknown error occurs when trying to create and save a new todo list")
            return HttpResponse("Request failed when operating on database")
        # return HttpResponse("Success!")  # Sending an success response
        context = {
            'user_not_found': user_not_found,
        }
        return HttpResponse("Success!")
        # return redirect("index")
    else:
        return HttpResponse("Request method is not a Post")


# Register a new user account
def register_request(request):
    """
    Handles user registration. If the request method is POST, it validates the form data and creates a new user.
    On successful registration, it logs in the user and redirects to the index page. If registration fails, it 
    displays an error message.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Redirects to the index page or renders the registration form with error messages.
    """
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            print(user)

            # Add a empty list to SharedList table
            shared_list = SharedList(user=User.objects.get(username=user), shared_list_id="")
            shared_list.save()

            login(request, user)
            messages.success(request, "Registration successful." )
            return redirect("todo:index")
        messages.error(request, "Unsuccessful registration. Invalid information.")
    form = NewUserForm()
    return render(request=request, template_name="todo/register.html", context={"register_form":form, 'config': config})

# Social login
@csrf_exempt
def social_login(request):
    """
    Handles social login via Google. This function verifies the token received from Google, retrieves user data, 
    and either logs in an existing user or creates a new user account.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Redirects to the index page or returns a 403 status on token verification failure.
    """
    token = request.POST.get('credential')
    
    try:
        # Verify the token with Google's API
        user_data = id_token.verify_oauth2_token(
            token, requests.Request(), "736572233255-usvqanirqiarbk9ffhl6t6tl9br651fn.apps.googleusercontent.com"
        )
        
        # Extract necessary user information
        email = user_data.get('email')
        first_name = user_data.get('given_name')
        last_name = user_data.get('family_name')
        
        # Create or retrieve user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],  # Ensure a unique username
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        
        # Authenticate and log in the user
        if created:
            user.set_unusable_password()  # Optional: set an unusable password for Google-only login
            user.save()
        
        # Log the user in
        login(request, user)
        
        # Optional: Store additional data in session or profile model
        # request.session['profile_picture'] = user_data.get('picture')
        
        return redirect("todo:index")
    
    except ValueError:
        return HttpResponse(status=403)


# Login a user
def login_request(request):
    """
    Handles user login. If the request method is POST, it validates the login form and authenticates the user.
    On successful authentication, it logs in the user and redirects to the index page. If authentication fails, 
    it displays an error message.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Redirects to the index page or renders the login form with error messages.
    """
	if request.method == "POST":
		form = AuthenticationForm(request, data=request.POST)
		if form.is_valid():
			username = form.cleaned_data.get('username')
			password = form.cleaned_data.get('password')
			user = authenticate(username=username, password=password)
			if user is not None:
				login(request, user)
				messages.info(request, f"You are now logged in as {username}.")
				return redirect("todo:index")
			else:
				messages.error(request,"Invalid username or password.")
		else:
			messages.error(request,"Invalid username or password.")
	form = AuthenticationForm()
	return render(request=request, template_name="todo/login.html", context={"login_form":form, "config": config})


# Logout a user
def logout_request(request):
    """
    Handles user logout. Logs out the user and redirects to the index page with a success message.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Redirects to the index page with a logout message.
    """
	logout(request)
	messages.info(request, "You have successfully logged out.")
	return redirect("todo:index")


# Reset user password
def password_reset_request(request):
    """
    Handles password reset requests. If the request method is POST, it validates the email and sends a password 
    reset email if the user exists. It renders the password reset form otherwise.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Renders the password reset form or redirects after sending the email.
    """
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "todo/password/password_reset_email.txt"
                    c = {
					"email":user.email,
					'domain':'127.0.0.1:8000',
					'site_name': 'Website',
					"uid": urlsafe_base64_encode(force_bytes(user.pk)),
					"user": user,
					'token': default_token_generator.make_token(user),
					'protocol': 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        send_email = EmailMessage(subject, email, settings.EMAIL_HOST_USER, [user.email])
                        send_email.fail_silently = False
                        send_email.send()
                    except BadHeaderError:
                        return HttpResponse('Invalid header found')                  
                    return redirect("/password_reset/done/")
            else:
                messages.error(request, "Not an Email from existing users!")
        else:
            messages.error(request, "Not an Email from existing users!")
    
    password_reset_form = PasswordResetForm()
    return render(request=request, template_name="todo/password/password_reset.html", context={"password_reset_form":password_reset_form, "config": config})

# Delete a template
@require_POST
def delete_template(request, template_id):
    """
    Deletes a specified template if the user is authenticated. If the user is not authenticated,
    they are redirected to the login page. If the template exists, it is deleted and the user
    is redirected to the templates list page.

    Args:
        request: The HTTP request object.
        template_id (int): The ID of the template to be deleted.

    Returns:
        HttpResponse: Redirects to the login page if the user is not authenticated, 
                      or redirects to the templates list page after deletion.
    """
    if not request.user.is_authenticated:
        return redirect("/login")
    template = get_object_or_404(Template, id=template_id)
    if template:
        template.delete()
    return redirect('/templates')