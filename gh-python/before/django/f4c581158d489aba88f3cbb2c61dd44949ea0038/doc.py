import os
import re
import inspect
from django.core import meta
from django import templatetags
from django.conf import settings
from django.models.core import sites
from django.views.decorators.cache import cache_page
from django.core.extensions import CMSContext as Context
from django.core.exceptions import Http404, ViewDoesNotExist
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect
from django.core import template, template_loader, defaulttags, defaultfilters, urlresolvers
try:
    from django.parts.admin import doc
except ImportError:
    doc = None
    
# Exclude methods starting with these strings from documentation
MODEL_METHODS_EXCLUDE = ('_', 'add_', 'delete', 'save', 'set_')

def doc_index(request):
    if not doc:
        return missing_docutils_page(request)
        
    t = template_loader.get_template('doc/index')
    c = Context(request, {})
    return HttpResponse(t.render(c))
    
def bookmarklets(request):
    t = template_loader.get_template('doc/bookmarklets')
    c = Context(request, {
        'admin_url' : "%s://%s" % (os.environ.get('HTTPS') == 'on' and 'https' or 'http', request.META['HTTP_HOST']),
    })
    return HttpResponse(t.render(c))

def template_tag_index(request):
    if not doc:
        return missing_docutils_page(request)
        
    # We have to jump through some hoops with registered_tags to make sure 
    # they don't get messed up by loading outside tagsets
    saved_tagset = template.registered_tags.copy(), template.registered_filters.copy()      
    load_all_installed_template_libraries()

    # Gather docs
    tags = []
    for tagname in template.registered_tags:
        title, body, metadata = doc.parse_docstring(template.registered_tags[tagname].__doc__)
        if title:
            title = doc.parse_rst(title, 'tag', 'tag:' + tagname)
        if body:
            body = doc.parse_rst(body, 'tag', 'tag:' + tagname)
        for key in metadata:
            metadata[key] = doc.parse_rst(metadata[key], 'tag', 'tag:' + tagname)
        library = template.registered_tags[tagname].__module__.split('.')[-1]
        if library == 'template_loader' or library == 'defaulttags':
            library = None
        tags.append({
            'name'    : tagname,
            'title'   : title,
            'body'    : body,
            'meta'    : metadata,
            'library' : library,
        })

    # Fix registered_tags
    template.registered_tags, template.registered_filters = saved_tagset

    t = template_loader.get_template('doc/template_tag_index')
    c = Context(request, {
        'tags' : tags,
    })
    return HttpResponse(t.render(c))
template_tag_index = cache_page(template_tag_index, 15*60)

def template_filter_index(request):
    if not doc:
        return missing_docutils_page(request)
        
    saved_tagset = template.registered_tags.copy(), template.registered_filters.copy()      
    load_all_installed_template_libraries()

    filters = []
    for filtername in template.registered_filters:
        title, body, metadata = doc.parse_docstring(template.registered_filters[filtername][0].__doc__)
        if title:
            title = doc.parse_rst(title, 'filter', 'filter:' + filtername)
        if body:
            body = doc.parse_rst(body, 'filter', 'filter:' + filtername)
        for key in metadata:
            metadata[key] = doc.parse_rst(metadata[key], 'filter', 'filter:' + filtername)
        metadata['AcceptsArgument'] = template.registered_filters[filtername][1]
        library = template.registered_filters[filtername][0].__module__.split('.')[-1]
        if library == 'template_loader' or library == 'defaultfilters':
            library = None
        filters.append({
            'name'    : filtername,
            'title'   : title,
            'body'    : body,
            'meta'    : metadata,
            'library' : library,
        })

    template.registered_tags, template.registered_filters = saved_tagset

    t = template_loader.get_template('doc/template_filter_index')
    c = Context(request, {
        'filters' : filters,
    })
    return HttpResponse(t.render(c))
template_filter_index = cache_page(template_filter_index, 15*60)

def view_index(request):
    if not doc:
        return missing_docutils_page(request)

    views = []
    for site_settings_module in settings.ADMIN_FOR:
        settings_mod = __import__(site_settings_module, '', '', [''])
        urlconf = __import__(settings_mod.ROOT_URLCONF, '', '', [''])
        view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns)
        for (func, regex) in view_functions:
            title, body, metadata = doc.parse_docstring(func.__doc__)
            if title:
                title = doc.parse_rst(title, 'view', 'view:' + func.__name__)
            views.append({
                'name'   : func.__name__,
                'module' : func.__module__,
                'title'  : title,
                'site_id': settings_mod.SITE_ID,
                'site'   : sites.get_object(id__exact=settings_mod.SITE_ID),
                'url'    : simplify_regex(regex),
            })
    t = template_loader.get_template('doc/view_index')
    c = Context(request, {
        'views' : views,
    })
    return HttpResponse(t.render(c))
view_index = cache_page(view_index, 15*60)

def view_detail(request, view):
    if not doc:
        return missing_docutils_page(request)

    mod, func = urlresolvers.get_mod_func(view)
    try:
        view_func = getattr(__import__(mod, '', '', ['']), func)
    except (ImportError, AttributeError):
        raise Http404
    title, body, metadata = doc.parse_docstring(view_func.__doc__)
    if title:
        title = doc.parse_rst(title, 'view', 'view:' + view)
    if body:
        body = doc.parse_rst(body, 'view', 'view:' + view)
    for key in metadata:
        metadata[key] = doc.parse_rst(metadata[key], 'view', 'view:' + view)
    t = template_loader.get_template('doc/view_detail')
    c = Context(request, {
        'name'      : view,
        'summary'   : title,
        'body'      : body,
        'meta'      : metadata,
    })
    return HttpResponse(t.render(c))

def model_index(request):
    if not doc:
        return missing_docutils_page(request)

    models = []
    for app in meta.get_installed_model_modules():
        for model in app._MODELS:
            opts = model._meta
            models.append({
                'name'   : '%s.%s' % (opts.app_label, opts.module_name),
                'module' : opts.app_label,
                'class'  : opts.module_name,
            })
    t = template_loader.get_template('doc/model_index')
    c = Context(request, {
        'models' : models,
    })
    return HttpResponse(t.render(c))

def model_detail(request, model):
    if not doc:
        return missing_docutils_page(request)

    try:
        model = meta.get_app(model)
    except ImportError:
        raise Http404
    opts = model.Klass._meta
    
    # Gather fields/field descriptions
    fields = []
    for field in opts.fields:
        fields.append({
            'name'     : field.name,
            'data_type': get_readable_field_data_type(field),
            'verbose'  : field.verbose_name,
            'help'     : field.help_text,
        })
    for func_name, func in model.Klass.__dict__.items():
        if callable(func) and len(inspect.getargspec(func)[0]) == 0:
            try:
                for exclude in MODEL_METHODS_EXCLUDE:
                    if func_name.startswith(exclude):
                        raise StopIteration
            except StopIteration:
                continue
            verbose = func.__doc__
            if verbose:
                verbose = doc.parse_rst(doc.trim_docstring(verbose), 'model', 'model:' + opts.module_name)
            fields.append({
                'name'      : func_name,
                'data_type' : get_return_data_type(func_name),
                'verbose'   : verbose,
            })

    t = template_loader.get_template('doc/model_detail')
    c = Context(request, {
        'name'    : '%s.%s' % (opts.app_label, opts.module_name),
        'summary' : "Fields on %s objects" % opts.verbose_name,
        'fields'  : fields,
    })
    return HttpResponse(t.render(c))

####################
# Helper functions #
####################

def missing_docutils_page(request):
    """Display an error message for people without docutils"""
    t = template_loader.get_template('doc/missing_docutils')
    c = Context(request, {})
    return HttpResponse(t.render(c))

def load_all_installed_template_libraries():
    # Clear out and reload default tags
    template.registered_tags.clear()
    reload(defaulttags)
    reload(template_loader) # template_loader defines the block/extends tags

    # Load any template tag libraries from installed apps
    for e in templatetags.__path__:
        libraries = [os.path.splitext(p)[0] for p in os.listdir(e) if p.endswith('.py') and p[0].isalpha()]
        for lib in libraries:
            try:
                mod = defaulttags.LoadNode.load_taglib(lib)
                reload(mod)
            except ImportError:
                pass
                
def get_return_data_type(func_name):
    """Return a somewhat-helpful data type given a function name"""
    if func_name.startswith('get_'):
        if func_name.endswith('_list'):
            return 'List'
        elif func_name.endswith('_count'):
            return 'Integer'
    return ''

# Maps Field objects to their human-readable data types, as strings.
# Column-type strings can contain format strings; they'll be interpolated
# against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPE_MAPPING = {
    'AutoField'                 : 'Integer',
    'BooleanField'              : 'Boolean (Either True or False)',
    'CharField'                 : 'String (up to %(maxlength)s)',
    'CommaSeparatedIntegerField': 'Comma-separated integers',
    'DateField'                 : 'Date (without time)',
    'DateTimeField'             : 'Date (with time)',
    'EmailField'                : 'E-mail address',
    'FileField'                 : 'File path',
    'FloatField'                : 'Decimal number',
    'ImageField'                : 'File path',
    'IntegerField'              : 'Integer',
    'IPAddressField'            : 'IP address',
    'ManyToManyField'           : '',
    'NullBooleanField'          : 'Boolean (Either True, False or None)',
    'PhoneNumberField'          : 'Phone number',
    'PositiveIntegerField'      : 'Integer',
    'PositiveSmallIntegerField' : 'Integer',
    'SlugField'                 : 'String (up to 50)',
    'SmallIntegerField'         : 'Integer',
    'TextField'                 : 'Text',
    'TimeField'                 : 'Time',
    'URLField'                  : 'URL',
    'USStateField'              : 'U.S. state (two uppercase letters)',
    'XMLField'                  : 'XML text',
}

def get_readable_field_data_type(field):    
    return DATA_TYPE_MAPPING[field.__class__.__name__] % field.__dict__

def extract_views_from_urlpatterns(urlpatterns, base=''):
    """
    Return a list of views from a list of urlpatterns.
    
    Each object in the returned list is a two-tuple: (view_func, regex)
    """
    views = []
    for p in urlpatterns:
        if hasattr(p, 'get_callback'):
            try:
                views.append((p.get_callback(), base + p.regex.pattern))
            except ViewDoesNotExist:
                continue
        elif hasattr(p, 'get_url_patterns'):
            views.extend(extract_views_from_urlpatterns(p.get_url_patterns(), base + p.regex.pattern))
        else:
            raise TypeError, "%s does not appear to be a urlpattern object" % p
    return views

# Clean up urlpattern regexes into something somewhat readable by Mere Humans:
# turns something like "^(?P<sport_slug>\w+)/athletes/(?P<athlete_slug>\w+)/$"
# into "<sport_slug>/athletes/<athlete_slug>/"

named_group_matcher = re.compile(r'\(\?P(<\w+>).+?\)')

def simplify_regex(pattern):
    pattern = named_group_matcher.sub(lambda m: m.group(1), pattern)
    pattern = pattern.replace('^', '').replace('$', '').replace('?', '').replace('//', '/')
    if not pattern.startswith('/'):
        pattern = '/' + pattern
    return pattern