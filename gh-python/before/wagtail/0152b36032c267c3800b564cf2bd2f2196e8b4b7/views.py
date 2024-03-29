from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import permission_required
from wagtail.wagtailadmin.edit_handlers import ObjectList

import models
import forms


REDIRECT_EDIT_HANDLER = ObjectList(models.Redirect.content_panels)

@permission_required('wagtailredirects.change_redirect')
def index(request):
    # Get redirects
    redirects = models.Redirect.get_for_site(site=request.site)

    # Render template
    return render(request, "wagtailredirects/index.html", {
        'redirects': redirects,
    })


@permission_required('wagtailredirects.change_redirect')
def edit(request, redirect_id):
    theredirect = get_object_or_404(models.Redirect, id=redirect_id)

    form_class = REDIRECT_EDIT_HANDLER.get_form_class(models.Redirect)
    if request.POST:
        form = form_class(request.POST, request.FILES, instance=theredirect)
        if form.is_valid():
            form.save()
            messages.success(request, "Redirect '%s' updated." % theredirect.title)
            return redirect('wagtailredirects_index')
        else:
            messages.error(request, "The redirect could not be saved due to errors.")
            edit_handler = REDIRECT_EDIT_HANDLER(instance=theredirect, form=form)
    else:
        form = form_class(instance=theredirect)
        edit_handler = REDIRECT_EDIT_HANDLER(instance=theredirect, form=form)

    return render(request, "wagtailredirects/edit.html", {
        'redirect': theredirect,
        'edit_handler': edit_handler,
    })


@permission_required('wagtailredirects.change_redirect')
def delete(request, redirect_id):
    theredirect = get_object_or_404(models.Redirect, id=redirect_id)

    if request.POST:
        theredirect.delete()
        messages.success(request, "Redirect '%s' deleted." % theredirect.title)
        return redirect('wagtailredirects_index')

    return render(request, "wagtailredirects/confirm_delete.html", {
        'redirect': theredirect,
    })


@permission_required('wagtailredirects.change_redirect')
def add(request):
    theredirect = models.Redirect()

    form_class = REDIRECT_EDIT_HANDLER.get_form_class(models.Redirect)
    if request.POST:
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            theredirect = form.save(commit=False)
            theredirect.site = request.site
            theredirect.save()

            messages.success(request, "Redirect '%s' added." % theredirect.title)
            return redirect('wagtailredirects_index')
        else:
            messages.error(request, "The redirect could not be created due to errors.")
            edit_handler = REDIRECT_EDIT_HANDLER(instance=theredirect, form=form)
    else:
        form = form_class()
        edit_handler = REDIRECT_EDIT_HANDLER(instance=theredirect, form=form)

    return render(request, "wagtailredirects/add.html", {
        'edit_handler': edit_handler,
    })