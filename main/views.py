from django.shortcuts import render
import django.shortcuts
from django.contrib.auth.decorators import login_required

# Create your views here.
def home(request):
    return django.shortcuts.render(request, 'main/home.html') 

def login_view(request):
    return django.shortcuts.render(request, 'users/login.html')

def signup_view(request):
    return django.shortcuts.render(request, 'users/signup.html')

def logout_view(request):
    return django.shortcuts.redirect('home')



@login_required
def home(request):

    return django.shortcuts.render(
        request,
        'main/home.html'
    )
    
    from django.shortcuts import render


@login_required
def home(request):

    context = {
        'total_students': 0,
        'total_routes': 0,
        'total_supervisors': 0
    }

    return render(
        request,
        'main/home.html',
        context
    )