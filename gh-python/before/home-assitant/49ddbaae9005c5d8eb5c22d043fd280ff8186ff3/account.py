from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm


def account(request):
    return render(request, 'wagtailadmin/account/account.html')


def change_password(request):
    can_change_password = request.user.has_usable_password()

    if can_change_password:
        if request.POST:
            form = SetPasswordForm(request.user, request.POST)

            if form.is_valid():
                form.save()

                messages.success(request, "Your password has been changed successfully!")
                return redirect('wagtailadmin_account')
        else:
            form = SetPasswordForm(request.user)
    else:
        form = None

    return render(request, 'wagtailadmin/account/change_password.html', {
        'form': form,
        'can_change_password': can_change_password,
    })