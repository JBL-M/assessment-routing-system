import django.shortcuts

# Create your views here.
def home(request):
    return django.shortcuts.render(request, 'main/home.html') 

def login_view(request):
    return django.shortcuts.render(request, 'users/login.html')

def signup_view(request):
    return django.shortcuts.render(request, 'users/signup.html')

def logout_view(request):
    return django.shortcuts.redirect('home')