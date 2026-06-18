from django.shortcuts import redirect, render
from .forms import RegisterForm
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout

def register_view(request):

    if request.method == 'POST':

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save(commit=False)

            user.set_password(
                form.cleaned_data['password']
            )

            user.save()

            return redirect('login')

    else:
        form = RegisterForm()

    return render(
        request,
        'users/register.html',
        {'form': form}
    )


def login_view(request):

    if request.method == 'POST':

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect('login')

    return render(
        request,
        'users/login.html'
    )


def logout_view(request):

    logout(request)

    return redirect('login')