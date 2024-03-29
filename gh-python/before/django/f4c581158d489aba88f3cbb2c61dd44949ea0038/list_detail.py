from django import models
from django.core import template_loader
from django.utils.httpwrappers import HttpResponse
from django.core.xheaders import populate_xheaders
from django.core.extensions import CMSContext as Context
from django.core.paginator import ObjectPaginator, InvalidPage
from django.core.exceptions import Http404, ObjectDoesNotExist

def object_list(request, app_label, module_name, paginate_by=None, allow_empty=False, template_name=None, extra_lookup_kwargs={}, extra_context=None):
    """
    Generic list of objects.

    Templates: ``<app_label>/<module_name>_list``
    Context:
        object_list
            list of objects
        is_paginated
            are the results paginated?
        results_per_page
            number of objects per page (if paginated)
        has_next
            is there a next page?
        has_previous
            is there a prev page?
        page
            the current page
        next
            the next page
        previous
            the previous page
        pages
            number of pages, total
    """
    mod = models.get_module(app_label, module_name)
    lookup_kwargs = extra_lookup_kwargs.copy()
    if paginate_by:
        paginator = ObjectPaginator(mod, lookup_kwargs, paginate_by)
        page = request.GET.get('page', 0)
        try:
            object_list = paginator.get_page(page)
        except InvalidPage:
            raise Http404
        page = int(page)
        c = Context(request, {
            'object_list': object_list,
            'is_paginated' : True,
            'results_per_page' : paginate_by,
            'has_next': paginator.has_next_page(page),
            'has_previous': paginator.has_previous_page(page),
            'page': page + 1,
            'next': page + 1,
            'previous': page - 1,
            'pages': paginator.pages,
        })
    else:
        object_list = mod.get_list(**lookup_kwargs)
        c = Context(request, {
            'object_list' : object_list,
            'is_paginated' : False
        })
    if len(object_list) == 0 and not allow_empty:
        raise Http404
    if extra_context:
        c.update(extra_context)
    if not template_name:
        template_name = "%s/%s_list" % (app_label, module_name)
    t = template_loader.get_template(template_name)
    return HttpResponse(t.render(c))

def object_detail(request, app_label, module_name, object_id=None, slug=None, slug_field=None, template_name=None, template_name_field=None, extra_lookup_kwargs={}, extra_context=None):
    """
    Generic list of objects.

    Templates: ``<app_label>/<module_name>_list``
    Context:
        object
            the object (whoa!)
    """
    mod = models.get_module(app_label, module_name)
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % mod.Klass._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError("Generic detail view must be called with either an object_id or a slug/slug_field")
    lookup_kwargs.update(extra_lookup_kwargs)
    try:
        object = mod.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404("%s.%s does not exist for %s" % (app_label, module_name, lookup_kwargs))
    if not template_name:
        template_name = "%s/%s_detail" % (app_label, module_name)
    if template_name_field:
        template_name_list = [getattr(object, template_name_field), template_name]
        t = template_loader.select_template(template_name_list)
    else:
        t = template_loader.get_template(template_name)
    c = Context(request, {
        'object' : object,
    })
    if extra_context:
        c.update(extra_context)
    response = HttpResponse(t.render(c))
    populate_xheaders(request, response, app_label, module_name, getattr(object, object._meta.pk.name))
    return response
