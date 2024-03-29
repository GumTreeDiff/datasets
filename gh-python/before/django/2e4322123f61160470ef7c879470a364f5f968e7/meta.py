from django.core import formfields, validators
from django.core import db
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
import copy, datetime, os, re, sys, types

# The values to use for "blank" in SelectFields. Will be appended to the start of most "choices" lists.
BLANK_CHOICE_DASH = [("", "---------")]
BLANK_CHOICE_NONE = [("", "None")]

# Admin stages.
ADD, CHANGE, BOTH = 1, 2, 3

# Values for Relation.edit_inline_type.
TABULAR, STACKED = 1, 2

# Values for filter_interface.
HORIZONTAL, VERTICAL = 1, 2

# Random entropy string used by "default" param.
NOT_PROVIDED = 'oijpwojefiojpanv'

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

# Prefix (in python path style) to location of models.
MODEL_PREFIX = 'django.models'

# Methods on models with the following prefix will be removed and
# converted to module-level functions.
MODEL_FUNCTIONS_PREFIX = '_module_'

# Methods on models with the following prefix will be removed and
# converted to manipulator methods.
MANIPULATOR_FUNCTIONS_PREFIX = '_manipulator_'

LOOKUP_SEPARATOR = '__'

RECURSIVE_RELATIONSHIP_CONSTANT = 'self'

####################
# HELPER FUNCTIONS #
####################

# capitalizes first letter of string
capfirst = lambda x: x and x[0].upper() + x[1:]

# prepares a value for use in a LIKE query
prep_for_like_query = lambda x: str(x).replace("%", "\%").replace("_", "\_")

# returns the <ul> class for a given radio_admin value
get_ul_class = lambda x: 'radiolist%s' % ((x == HORIZONTAL) and ' inline' or '')

def curry(*args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return args[0](*(args[1:]+moreargs), **dict(kwargs.items() + morekwargs.items()))
    return _curried

def get_module(app_label, module_name):
    return __import__('%s.%s.%s' % (MODEL_PREFIX, app_label, module_name), '', '', [''])

def get_app(app_label):
    return __import__('%s.%s' % (MODEL_PREFIX, app_label), '', '', [''])

_installed_models_cache = None
def get_installed_models():
    """
    Returns a list of installed "models" packages, such as foo.models,
    ellington.news.models, etc. This does NOT include django.models.
    """
    global _installed_models_cache
    if _installed_models_cache is not None:
        return _installed_models_cache
    _installed_models_cache = []
    for a in settings.INSTALLED_APPS:
        try:
            _installed_models_cache.append(__import__(a + '.models', '', '', ['']))
        except ImportError:
            pass
    return _installed_models_cache

_installed_modules_cache = None
def get_installed_model_modules(core_models=None):
    """
    Returns a list of installed models, such as django.models.core,
    ellington.news.models.news, foo.models.bar, etc.
    """
    global _installed_modules_cache
    if _installed_modules_cache is not None:
        return _installed_modules_cache
    _installed_modules_cache = []

    # django.models is a special case.
    for submodule in (core_models or []):
        _installed_modules_cache.append(__import__('django.models.%s' % submodule, '', '', ['']))
    for m in get_installed_models():
        for submodule in getattr(m, '__all__', []):
            _installed_modules_cache.append(__import__('django.models.%s' % submodule, '', '', ['']))
    return _installed_modules_cache

class LazyDate:
    """
    Use in limit_choices_to to compare the field to dates calculated at run time
    instead of when the model is loaded.  For example::

        ... limit_choices_to = {'date__gt' : meta.LazyDate(days=-3)} ...

    which will limit the choices to dates greater than three days ago.
    """
    def __init__(self, **kwargs):
        self.delta = datetime.timedelta(**kwargs)

    def __str__(self):
        return str(self.__get_value__())

    def __repr__(self):
        return "<LazyDate: %s>" % self.delta

    def __get_value__(self):
        return datetime.datetime.now() + self.delta

################
# MAIN CLASSES #
################

class FieldDoesNotExist(Exception):
    pass

class BadKeywordArguments(Exception):
    pass

class Options:
    def __init__(self, module_name='', verbose_name='', verbose_name_plural='', db_table='',
        fields=None, ordering=None, unique_together=None, admin=None, has_related_links=False,
        where_constraints=None, object_name=None, app_label=None,
        exceptions=None, permissions=None, get_latest_by=None,
        order_with_respect_to=None, module_constants=None):

        # Save the original function args, for use by copy(). Note that we're
        # NOT using copy.deepcopy(), because that would create a new copy of
        # everything in memory, and it's better to conserve memory. Of course,
        # this comes with the important gotcha that changing any attribute of
        # this object will change its value in self._orig_init_args, so we
        # need to be careful not to do that. In practice, we can pull this off
        # because Options are generally read-only objects, and __init__() is
        # the only place where its attributes are manipulated.

        # locals() is used purely for convenience, so we don't have to do
        # something verbose like this:
        #    self._orig_init_args = {
        #       'module_name': module_name,
        #       'verbose_name': verbose_name,
        #       ...
        #    }
        self._orig_init_args = locals()
        del self._orig_init_args['self'] # because we don't care about it.

        # Move many-to-many related fields from self.fields into self.many_to_many.
        self.fields, self.many_to_many = [], []
        for field in (fields or []):
            if field.rel and isinstance(field.rel, ManyToMany):
                self.many_to_many.append(field)
            else:
                self.fields.append(field)
        self.module_name, self.verbose_name = module_name, verbose_name
        self.verbose_name_plural = verbose_name_plural or verbose_name + 's'
        self.db_table, self.has_related_links = db_table, has_related_links
        self.ordering = ordering or []
        self.unique_together = unique_together or []
        self.where_constraints = where_constraints or []
        self.exceptions = exceptions or []
        self.permissions = permissions or []
        self.object_name, self.app_label = object_name, app_label
        self.get_latest_by = get_latest_by
        if order_with_respect_to:
            self.order_with_respect_to = self.get_field(order_with_respect_to)
            self.ordering = (('_order', 'ASC'),)
        else:
            self.order_with_respect_to = None
        self.module_constants = module_constants or {}
        # Alter the admin attribute so that the 'fields' members are lists of
        # field objects -- not lists of field names.
        if admin:
            # Be sure to use admin.copy(), because otherwise we'll be editing a
            # reference of admin, which will in turn affect the copy in
            # self._orig_init_args.
            self.admin = admin.copy()
            for fieldset in self.admin.fields:
                admin_fields = []
                for field_name_or_list in fieldset[1]['fields']:
                    if isinstance(field_name_or_list, basestring):
                        admin_fields.append([self.get_field(field_name_or_list)])
                    else:
                        admin_fields.append([self.get_field(field_name) for field_name in field_name_or_list])
                fieldset[1]['fields'] = admin_fields
        else:
            self.admin = None

        # Calculate one_to_one_field.
        self.one_to_one_field = None
        for f in self.fields:
            if isinstance(f.rel, OneToOne):
                self.one_to_one_field = f
                break
        # Cache the primary-key field.
        self.pk = None
        for f in self.fields:
            if f.primary_key:
                self.pk = f
                break
        # If a primary_key field hasn't been specified, add an
        # auto-incrementing primary-key ID field automatically.
        if self.pk is None:
            self.fields.insert(0, AutoField('id', 'ID', primary_key=True))
            self.pk = self.fields[0]

    def __repr__(self):
        return '<Options for %s>' % self.module_name

    def copy(self, **kwargs):
        args = self._orig_init_args.copy()
        args.update(kwargs)
        return self.__class__(**args)

    def get_model_module(self):
        return get_module(self.app_label, self.module_name)

    def get_content_type_id(self):
        "Returns the content-type ID for this object type."
        if not hasattr(self, '_content_type_id'):
            mod = get_module('core', 'contenttypes')
            self._content_type_id = mod.get_object(python_module_name__exact=self.module_name, package__label__exact=self.app_label).id
        return self._content_type_id

    def get_field(self, name, many_to_many=True):
        """
        Returns the requested field by name. Raises FieldDoesNotExist on error.
        """
        to_search = many_to_many and (self.fields + self.many_to_many) or self.fields
        for f in to_search:
            if f.name == name:
                return f
        raise FieldDoesNotExist, "name=%s" % name

    def get_order_sql(self, table_prefix=''):
        "Returns the full 'ORDER BY' clause for this object, according to self.ordering."
        if not self.ordering: return ''
        pre = table_prefix and (table_prefix + '.') or ''
        return 'ORDER BY ' + ','.join(['%s%s %s' % (pre, f, order) for f, order in self.ordering])

    def get_add_permission(self):
        return 'add_%s' % self.object_name.lower()

    def get_change_permission(self):
        return 'change_%s' % self.object_name.lower()

    def get_delete_permission(self):
        return 'delete_%s' % self.object_name.lower()

    def get_rel_object_method_name(self, rel_opts, rel_field):
        # This method encapsulates the logic that decides what name to give a
        # method that retrieves related many-to-one objects. Usually it just
        # uses the lower-cased object_name, but if the related object is in
        # another app, its app_label is appended.
        #
        # Examples:
        #
        #   # Normal case -- a related object in the same app.
        #   # This method returns "choice".
        #   Poll.get_choice_list()
        #
        #   # A related object in a different app.
        #   # This method returns "lcom_bestofaward".
        #   Place.get_lcom_bestofaward_list() # "lcom_bestofaward"
        rel_obj_name = rel_field.rel.related_name or rel_opts.object_name.lower()
        if self.app_label != rel_opts.app_label:
            rel_obj_name = '%s_%s' % (rel_opts.app_label, rel_obj_name)
        return rel_obj_name

    def get_all_related_objects(self):
        try: # Try the cache first.
            return self._all_related_objects
        except AttributeError:
            module_list = get_installed_model_modules()
            rel_objs = []
            for mod in module_list:
                for klass in mod._MODELS:
                    for f in klass._meta.fields:
                        if f.rel and self == f.rel.to:
                            rel_objs.append((klass._meta, f))
            if self.has_related_links:
                # Manually add RelatedLink objects, which are a special case.
                core = get_module('relatedlinks', 'relatedlinks')
                # Note that the copy() is very important -- otherwise any
                # subsequently loaded object with related links will override this
                # relationship we're adding.
                link_field = copy.copy(core.RelatedLink._meta.get_field('object_id'))
                link_field.rel = ManyToOne(self.get_model_module().Klass, 'related_links', 'id',
                    num_in_admin=3, min_num_in_admin=3, edit_inline=True, edit_inline_type=TABULAR,
                    lookup_overrides={
                        'content_type__package__label__exact': self.app_label,
                        'content_type__python_module_name__exact': self.module_name
                    })
                rel_objs.append((core.RelatedLink._meta, link_field))
            self._all_related_objects = rel_objs
            return rel_objs

    def get_inline_related_objects(self):
        return [(a, b) for a, b in self.get_all_related_objects() if b.rel.edit_inline]

    def get_all_related_many_to_many_objects(self):
        module_list = get_installed_model_modules()
        rel_objs = []
        for mod in module_list:
            for klass in mod._MODELS:
                try:
                    for f in klass._meta.many_to_many:
                        if f.rel and self == f.rel.to:
                            rel_objs.append((klass._meta, f))
                            raise StopIteration
                except StopIteration:
                    continue
        return rel_objs

    def get_ordered_objects(self):
        "Returns a list of Options objects that are ordered with respect to this object."
        if not hasattr(self, '_ordered_objects'):
            objects = []
            for klass in get_app(self.app_label)._MODELS:
                opts = klass._meta
                if opts.order_with_respect_to and opts.order_with_respect_to.rel \
                    and self == opts.order_with_respect_to.rel.to:
                    objects.append(opts)
            self._ordered_objects = objects
        return self._ordered_objects

    def has_field_type(self, field_type):
        """
        Returns True if this object's admin form has at least one of the given
        field_type (e.g. FileField).
        """
        if not hasattr(self, '_field_types'):
            self._field_types = {}
        if not self._field_types.has_key(field_type):
            try:
                # First check self.fields.
                for f in self.fields:
                    if isinstance(f, field_type):
                        raise StopIteration
                # Failing that, check related fields.
                for rel_obj, rel_field in self.get_inline_related_objects():
                    for f in rel_obj.fields:
                        if isinstance(f, field_type):
                            raise StopIteration
            except StopIteration:
                self._field_types[field_type] = True
            else:
                self._field_types[field_type] = False
        return self._field_types[field_type]

def _reassign_globals(function_dict, extra_globals, namespace):
    new_functions = {}
    for k, v in function_dict.items():
        # Get the code object.
        code = v.func_code
        # Recreate the function, but give it access to extra_globals and the
        # given namespace's globals, too.
        new_globals = {'__builtins__': __builtins__, 'db': db.db, 'datetime': datetime}
        new_globals.update(extra_globals.__dict__)
        func = types.FunctionType(code, globals=new_globals, name=k, argdefs=v.func_defaults)
        func.__dict__.update(v.__dict__)
        setattr(namespace, k, func)
        # For all of the custom functions that have been added so far, give
        # them access to the new function we've just created.
        for new_k, new_v in new_functions.items():
            new_v.func_globals[k] = func
        new_functions[k] = func

class ModelBase(type):
    "Metaclass for all models"
    def __new__(cls, name, bases, attrs):
        # If this isn't a subclass of Model, don't do anything special.
        if not bases:
            return type.__new__(cls, name, bases, attrs)

        # If this model is a subclass of another Model, create an Options
        # object by first copying the base class's _meta and then updating it
        # with the overrides from this class.
        replaces_module = None
        if bases[0] != Model:
            if not attrs.has_key('fields'):
                attrs['fields'] = list(bases[0]._meta._orig_init_args['fields'][:])
            if attrs.has_key('ignore_fields'):
                ignore_fields = attrs.pop('ignore_fields')
                new_fields = []
                for i, f in enumerate(attrs['fields']):
                    if f.name not in ignore_fields:
                        new_fields.append(f)
                attrs['fields'] = new_fields
            if attrs.has_key('add_fields'):
                attrs['fields'].extend(attrs.pop('add_fields'))
            if attrs.has_key('replaces_module'):
                # Set the replaces_module variable for now. We can't actually
                # do anything with it yet, because the module hasn't yet been
                # created.
                replaces_module = attrs.pop('replaces_module').split('.')
            # Pass any Options overrides to the base's Options instance, and
            # simultaneously remove them from attrs. When this is done, attrs
            # will be a dictionary of custom methods, plus __module__.
            meta_overrides = {}
            for k, v in attrs.items():
                if not callable(v) and k != '__module__':
                    meta_overrides[k] = attrs.pop(k)
            opts = bases[0]._meta.copy(**meta_overrides)
            opts.object_name = name
            del meta_overrides
        else:
            opts = Options(
                # If the module_name wasn't given, use the class name
                # in lowercase, plus a trailing "s" -- a poor-man's
                # pluralization.
                module_name = attrs.pop('module_name', name.lower() + 's'),
                # If the verbose_name wasn't given, use the class name,
                # converted from InitialCaps to "lowercase with spaces".
                verbose_name = attrs.pop('verbose_name',
                    re.sub('([A-Z])', ' \\1', name).lower().strip()),
                verbose_name_plural = attrs.pop('verbose_name_plural', ''),
                db_table = attrs.pop('db_table', ''),
                fields = attrs.pop('fields'),
                ordering = attrs.pop('ordering', None),
                unique_together = attrs.pop('unique_together', None),
                admin = attrs.pop('admin', None),
                has_related_links = attrs.pop('has_related_links', False),
                where_constraints = attrs.pop('where_constraints', None),
                object_name = name,
                app_label = attrs.pop('app_label', None),
                exceptions = attrs.pop('exceptions', None),
                permissions = attrs.pop('permissions', None),
                get_latest_by = attrs.pop('get_latest_by', None),
                order_with_respect_to = attrs.pop('order_with_respect_to', None),
                module_constants = attrs.pop('module_constants', None),
            )

        # Dynamically create the module that will contain this class and its
        # associated helper functions.
        if replaces_module is not None:
            new_mod = get_module(*replaces_module)
        else:
            new_mod = types.ModuleType(opts.module_name)

        # Collect any/all custom class methods and module functions, and move
        # them to a temporary holding variable. We'll deal with them later.
        if replaces_module is not None:
            # Initialize these values to the base class' custom_methods and
            # custom_functions.
            custom_methods = dict([(k, v) for k, v in new_mod.Klass.__dict__.items() if hasattr(v, 'custom')])
            custom_functions = dict([(k, v) for k, v in new_mod.__dict__.items() if hasattr(v, 'custom')])
        else:
            custom_methods, custom_functions = {}, {}
        manipulator_methods = {}
        for k, v in attrs.items():
            if k in ('__module__', '__init__', '_overrides', '__doc__'):
                continue # Skip the important stuff.
            # Give the function a function attribute "custom" to designate that
            # it's a custom function/method.
            v.custom = True
            if k.startswith(MODEL_FUNCTIONS_PREFIX):
                custom_functions[k[len(MODEL_FUNCTIONS_PREFIX):]] = v
            elif k.startswith(MANIPULATOR_FUNCTIONS_PREFIX):
                manipulator_methods[k[len(MANIPULATOR_FUNCTIONS_PREFIX):]] = v
            else:
                custom_methods[k] = v
            del attrs[k]

        # Create the module-level ObjectDoesNotExist exception.
        dne_exc_name = '%sDoesNotExist' % name
        does_not_exist_exception = types.ClassType(dne_exc_name, (ObjectDoesNotExist,), {})
        # Explicitly set its __module__ because it will initially (incorrectly)
        # be set to the module the code is being executed in.
        does_not_exist_exception.__module__ = MODEL_PREFIX + '.' + opts.module_name
        setattr(new_mod, dne_exc_name, does_not_exist_exception)

        # Create other exceptions.
        for exception_name in opts.exceptions:
            exc = types.ClassType(exception_name, (Exception,), {})
            exc.__module__ = MODEL_PREFIX + '.' + opts.module_name # Set this explicitly, as above.
            setattr(new_mod, exception_name, exc)

        # Create any module-level constants, if applicable.
        for k, v in opts.module_constants.items():
            setattr(new_mod, k, v)

        # Create the default class methods.
        attrs['__init__'] = curry(method_init, opts)
        attrs['__eq__'] = curry(method_eq, opts)
        attrs['save'] = curry(method_save, opts)
        attrs['save'].alters_data = True
        attrs['delete'] = curry(method_delete, opts)
        attrs['delete'].alters_data = True

        if opts.order_with_respect_to:
            attrs['get_next_in_order'] = curry(method_get_next_in_order, opts, opts.order_with_respect_to)
            attrs['get_previous_in_order'] = curry(method_get_previous_in_order, opts, opts.order_with_respect_to)

        for f in opts.fields:
            # If the object has a relationship to itself, as designated by
            # RECURSIVE_RELATIONSHIP_CONSTANT, create that relationship formally.
            if f.rel and f.rel.to == RECURSIVE_RELATIONSHIP_CONSTANT:
                f.rel.to = opts
            # Add "get_thingie" methods for many-to-one related objects.
            # EXAMPLES: Choice.get_poll(), Story.get_dateline()
            if isinstance(f.rel, ManyToOne):
                func = curry(method_get_many_to_one, f)
                func.__doc__ = "Returns the associated `%s.%s` object." % (f.rel.to.app_label, f.rel.to.module_name)
                attrs['get_%s' % f.rel.name] = func

        for f in opts.many_to_many:
            # Add "get_thingie" methods for many-to-many related objects.
            # EXAMPLES: Poll.get_sites(), Story.get_bylines()
            func = curry(method_get_many_to_many, f)
            func.__doc__ = "Returns a list of associated `%s.%s` objects." % (f.rel.to.app_label, f.rel.to.module_name)
            attrs['get_%s' % f.name] = func
            # Add "set_thingie" methods for many-to-many related objects.
            # EXAMPLES: Poll.set_sites(), Story.set_bylines()
            func = curry(method_set_many_to_many, f)
            func.__doc__ = "Resets this object's `%s.%s` list to the given list of IDs. Note that it doesn't check whether the given IDs are valid." % (f.rel.to.app_label, f.rel.to.module_name)
            func.alters_data = True
            attrs['set_%s' % f.name] = func

        # Create the class, because we need it to use in currying.
        new_class = type.__new__(cls, name, bases, attrs)

        # Give the class a docstring -- its definition.
        new_class.__doc__ = "%s.%s(%s)" % (opts.module_name, name, ", ".join([f.name for f in opts.fields]))

        # Create the standard, module-level API helper functions such
        # as get_object() and get_list().
        new_mod.get_object = curry(function_get_object, opts, new_class, does_not_exist_exception)
        new_mod.get_object.__doc__ = "Returns the %s object matching the given parameters." % name

        new_mod.get_list = curry(function_get_list, opts, new_class)
        new_mod.get_list.__doc__ = "Returns a list of %s objects matching the given parameters." % name

        new_mod.get_iterator = curry(function_get_iterator, opts, new_class)
        new_mod.get_iterator.__doc__ = "Returns an iterator of %s objects matching the given parameters." % name

        new_mod.get_count = curry(function_get_count, opts)
        new_mod.get_count.__doc__ = "Returns the number of %s objects matching the given parameters." % name

        new_mod._get_sql_clause = curry(function_get_sql_clause, opts)

        new_mod.get_in_bulk = curry(function_get_in_bulk, opts, new_class)
        new_mod.get_in_bulk.__doc__ = "Returns a dictionary of ID -> %s for the %s objects with IDs in the given id_list." % (name, name)

        if opts.get_latest_by:
            new_mod.get_latest = curry(function_get_latest, opts, new_class, does_not_exist_exception)

        for f in opts.fields:
            if isinstance(f, DateField) or isinstance(f, DateTimeField):
                # Add "get_next_by_thingie" and "get_previous_by_thingie" methods
                # for all DateFields and DateTimeFields that cannot be null.
                # EXAMPLES: Poll.get_next_by_pub_date(), Poll.get_previous_by_pub_date()
                if not f.null:
                    setattr(new_class, 'get_next_by_%s' % f.name, curry(method_get_next_or_previous, new_mod.get_object, f, True))
                    setattr(new_class, 'get_previous_by_%s' % f.name, curry(method_get_next_or_previous, new_mod.get_object, f, False))
                # Add "get_thingie_list" for all DateFields and DateTimeFields.
                # EXAMPLE: polls.get_pub_date_list()
                func = curry(function_get_date_list, opts, f)
                func.__doc__ = "Returns a list of days, months or years (as datetime.datetime objects) in which %s objects are available. The first parameter ('kind') must be one of 'year', 'month' or 'day'." % name
                setattr(new_mod, 'get_%s_list' % f.name, func)

            elif isinstance(f, FileField):
                setattr(new_class, 'get_%s_filename' % f.name, curry(method_get_file_filename, f))
                setattr(new_class, 'get_%s_url' % f.name, curry(method_get_file_url, f))
                setattr(new_class, 'get_%s_size' % f.name, curry(method_get_file_size, f))
                func = curry(method_save_file, f)
                func.alters_data = True
                setattr(new_class, 'save_%s_file' % f.name, func)
                if isinstance(f, ImageField):
                    # Add get_BLAH_width and get_BLAH_height methods, but only
                    # if the image field doesn't have width and height cache
                    # fields.
                    if not f.width_field:
                        setattr(new_class, 'get_%s_width' % f.name, curry(method_get_image_width, f))
                    if not f.height_field:
                        setattr(new_class, 'get_%s_height' % f.name, curry(method_get_image_height, f))

        # Add the class itself to the new module we've created.
        new_mod.__dict__[name] = new_class

        # Add "Klass" -- a shortcut reference to the class.
        new_mod.__dict__['Klass'] = new_class

        # Add the Manipulators.
        new_mod.__dict__['AddManipulator'] = get_manipulator(opts, new_class, manipulator_methods, add=True)
        new_mod.__dict__['ChangeManipulator'] = get_manipulator(opts, new_class, manipulator_methods, change=True)

        # Now that we have references to new_mod and new_class, we can add
        # any/all extra class methods to the new class. Note that we could
        # have just left the extra methods in attrs (above), but that would
        # have meant that any code within the extra methods would *not* have
        # access to module-level globals, such as get_list(), db, etc.
        # In order to give these methods access to those globals, we have to
        # deconstruct the method getting its raw "code" object, then recreating
        # the function with a new "globals" dictionary.
        #
        # To complicate matters more, because each method is manually assigned
        # a "globals" value, that "globals" value does NOT include the methods
        # that haven't been created yet. For instance, if there are two custom
        # methods, foo() and bar(), and foo() is created first, it won't have
        # bar() within its globals(). This is a problem because sometimes
        # custom methods/functions refer to other custom methods/functions. To
        # solve this problem, we keep track of the new functions created (in
        # the new_functions variable) and manually append each new function to
        # the func_globals() of all previously-created functions. So, by the
        # end of the loop, all functions will "know" about all the other
        # functions.
        _reassign_globals(custom_methods, new_mod, new_class)
        _reassign_globals(custom_functions, new_mod, new_mod)
        _reassign_globals(manipulator_methods, new_mod, new_mod.__dict__['AddManipulator'])
        _reassign_globals(manipulator_methods, new_mod, new_mod.__dict__['ChangeManipulator'])

        if hasattr(new_class, 'get_absolute_url'):
            new_class.get_absolute_url = curry(get_absolute_url, opts, new_class.get_absolute_url)

        # Get a reference to the module the class is in, and dynamically add
        # the new module to it.
        app_package = sys.modules.get(new_class.__module__)
        if replaces_module is not None:
            app_label = replaces_module[0]
        else:
            app_package.__dict__[opts.module_name] = new_mod
            app_label = app_package.__name__[app_package.__name__.rfind('.')+1:]

            # Populate the _MODELS member on the module the class is in.
            # Example: django.models.polls will have a _MODELS member that will
            # contain this list:
            # [<class 'django.models.polls.Poll'>, <class 'django.models.polls.Choice'>]
            # Don't do this if replaces_module is set.
            app_package.__dict__.setdefault('_MODELS', []).append(new_class)

        # Cache the app label.
        opts.app_label = app_label

        # If the db_table wasn't provided, use the app_label + module_name.
        if not opts.db_table:
            opts.db_table = "%s_%s" % (app_label, opts.module_name)
        new_class._meta = opts

        # Set the __file__ attribute to the __file__ attribute of its package,
        # because they're technically from the same file. Note: if we didn't
        # set this, sys.modules would think this module was built-in.
        try:
            new_mod.__file__ = app_package.__file__
        except AttributeError:
            # 'module' object has no attribute '__file__', which means the
            # class was probably being entered via the interactive interpreter.
            pass

        # Add the module's entry to sys.modules -- for instance,
        # "django.models.polls.polls". Note that "django.models.polls" has already
        # been added automatically.
        sys.modules.setdefault('%s.%s.%s' % (MODEL_PREFIX, app_label, opts.module_name), new_mod)

        # If this module replaces another one, get a reference to the other
        # module's parent, and replace the other module with the one we've just
        # created.
        if replaces_module is not None:
            old_app = get_app(replaces_module[0])
            setattr(old_app, replaces_module[1], new_mod)
            for i, model in enumerate(old_app._MODELS):
                if model._meta.module_name == replaces_module[1]:
                    # Replace the appropriate member of the old app's _MODELS
                    # data structure.
                    old_app._MODELS[i] = new_class
                    # Replace all relationships to the old class with
                    # relationships to the new one.
                    for rel_opts, rel_field in model._meta.get_all_related_objects():
                        rel_field.rel.to = opts
                    for rel_opts, rel_field in model._meta.get_all_related_many_to_many_objects():
                        rel_field.rel.to = opts
                    break

        return new_class

class Model:
    __metaclass__ = ModelBase

############################################
# HELPER FUNCTIONS (CURRIED MODEL METHODS) #
############################################

# CORE METHODS #############################

def method_init(opts, self, *args, **kwargs):
    for i, arg in enumerate(args):
        setattr(self, opts.fields[i].name, arg)
    for k, v in kwargs.items():
        try:
            opts.get_field(k, many_to_many=False)
        except FieldDoesNotExist:
            raise TypeError, "'%s' is an invalid keyword argument for this function" % k
        setattr(self, k, v)

def method_eq(opts, self, other):
    return isinstance(other, self.__class__) and getattr(self, opts.pk.name) == getattr(other, opts.pk.name)

def method_save(opts, self):
    # Run any pre-save hooks.
    if hasattr(self, '_pre_save'):
        self._pre_save()
    non_pks = [f for f in opts.fields if not f.primary_key]
    cursor = db.db.cursor()
    add = not bool(getattr(self, opts.pk.name))
    for f in non_pks:
        f.pre_save(self, getattr(self, f.name), add)
    db_values = [f.get_db_prep_save(getattr(self, f.name), add) for f in non_pks]
    # OneToOne objects are a special case because there's no AutoField, and the
    # primary key field is set manually.
    if isinstance(opts.pk.rel, OneToOne):
        cursor.execute("UPDATE %s SET %s WHERE %s=%%s" % \
            (opts.db_table, ','.join(['%s=%%s' % f.name for f in non_pks]),
            opts.pk.name), db_values + [getattr(self, opts.pk.name)])
        if cursor.rowcount == 0: # If nothing was updated, add the record.
            field_names = [f.name for f in opts.fields]
            placeholders = ['%s'] * len(field_names)
            cursor.execute("INSERT INTO %s (%s) VALUES (%s)" % \
                (opts.db_table, ','.join(field_names), ','.join(placeholders)),
                [f.get_db_prep_save(getattr(self, f.name), add=True) for f in opts.fields])
    else:
        if not add:
            cursor.execute("UPDATE %s SET %s WHERE %s=%%s" % \
                (opts.db_table, ','.join(['%s=%%s' % f.name for f in non_pks]),
                opts.pk.name), db_values + [getattr(self, opts.pk.name)])
        else:
            field_names = [f.name for f in non_pks]
            placeholders = ['%s'] * len(field_names)
            if opts.order_with_respect_to:
                field_names.append('_order')
                placeholders.append('(SELECT COUNT(*) FROM %s WHERE %s = %%s)' % \
                    (opts.db_table, opts.order_with_respect_to.name))
                db_values.append(getattr(self, opts.order_with_respect_to.name))
            cursor.execute("INSERT INTO %s (%s) VALUES (%s)" % \
                (opts.db_table, ','.join(field_names), ','.join(placeholders)), db_values)
            setattr(self, opts.pk.name, db.get_last_insert_id(cursor, opts.db_table, opts.pk.name))
    db.db.commit()
    # Run any post-save hooks.
    if hasattr(self, '_post_save'):
        self._post_save()

def method_delete(opts, self):
    assert getattr(self, opts.pk.name) is not None, "%r can't be deleted because it doesn't have an ID."
    cursor = db.db.cursor()
    for rel_opts, rel_field in opts.get_all_related_objects():
        rel_opts_name = opts.get_rel_object_method_name(rel_opts, rel_field)
        if isinstance(rel_field.rel, OneToOne):
            try:
                sub_obj = getattr(self, 'get_%s' % rel_opts_name)()
            except ObjectDoesNotExist:
                pass
            else:
                sub_obj.delete()
        else:
            for sub_obj in getattr(self, 'get_%s_list' % rel_opts_name)():
                sub_obj.delete()
    for rel_opts, rel_field in opts.get_all_related_many_to_many_objects():
        cursor.execute("DELETE FROM %s WHERE %s_id=%%s" % (rel_field.get_m2m_db_table(rel_opts),
            self._meta.object_name.lower()), [getattr(self, opts.pk.name)])
    cursor.execute("DELETE FROM %s WHERE %s=%%s" % (opts.db_table, opts.pk.name), [getattr(self, opts.pk.name)])
    db.db.commit()
    setattr(self, opts.pk.name, None)
    for f in opts.fields:
        if isinstance(f, FileField) and getattr(self, f.name):
            file_name = getattr(self, 'get_%s_filename' % f.name)()
            # If the file exists and no other object of this type references it,
            # delete it from the filesystem.
            if os.path.exists(file_name) and not opts.get_model_module().get_list(**{'%s__exact' % f.name: getattr(self, f.name)}):
                os.remove(file_name)

def method_get_next_in_order(opts, order_field, self):
    if not hasattr(self, '_next_in_order_cache'):
        self._next_in_order_cache = opts.get_model_module().get_object(order_by=(('_order', 'ASC'),),
            where=['_order > (SELECT _order FROM %s WHERE %s=%%s)' % (opts.db_table, opts.pk.name),
                '%s=%%s' % order_field.name], limit=1,
            params=[getattr(self, opts.pk.name), getattr(self, order_field.name)])
    return self._next_in_order_cache

def method_get_previous_in_order(opts, order_field, self):
    if not hasattr(self, '_previous_in_order_cache'):
        self._previous_in_order_cache = opts.get_model_module().get_object(order_by=(('_order', 'DESC'),),
            where=['_order < (SELECT _order FROM %s WHERE %s=%%s)' % (opts.db_table, opts.pk.name),
                '%s=%%s' % order_field.name], limit=1,
            params=[getattr(self, opts.pk.name), getattr(self, order_field.name)])
    return self._previous_in_order_cache

# RELATIONSHIP METHODS #####################

# Example: Story.get_dateline()
def method_get_many_to_one(field_with_rel, self):
    cache_var = field_with_rel.rel.get_cache_name()
    if not hasattr(self, cache_var):
        val = getattr(self, field_with_rel.name)
        mod = field_with_rel.rel.to.get_model_module()
        if val is None:
            raise getattr(mod, '%sDoesNotExist' % field_with_rel.rel.to.object_name)
        retrieved_obj = mod.get_object(**{'%s__exact' % field_with_rel.rel.field_name: val})
        setattr(self, cache_var, retrieved_obj)
    return getattr(self, cache_var)

# Handles getting many-to-many related objects.
# Example: Poll.get_sites()
def method_get_many_to_many(field_with_rel, self):
    rel = field_with_rel.rel.to
    cache_var = '_%s_cache' % field_with_rel.name
    if not hasattr(self, cache_var):
        mod = rel.get_model_module()
        sql = "SELECT %s FROM %s a, %s b WHERE a.%s = b.%s_id AND b.%s_id = %%s %s" % \
            (','.join(['a.%s' % f.name for f in rel.fields]), rel.db_table,
            field_with_rel.get_m2m_db_table(self._meta), rel.pk.name,
            rel.object_name.lower(), self._meta.object_name.lower(), rel.get_order_sql('a'))
        cursor = db.db.cursor()
        cursor.execute(sql, [getattr(self, self._meta.pk.name)])
        setattr(self, cache_var, [getattr(mod, rel.object_name)(*row) for row in cursor.fetchall()])
    return getattr(self, cache_var)

# Handles setting many-to-many relationships.
# Example: Poll.set_sites()
def method_set_many_to_many(rel_field, self, id_list):
    id_list = map(int, id_list) # normalize to integers
    current_ids = [obj.id for obj in method_get_many_to_many(rel_field, self)]
    ids_to_add, ids_to_delete = dict([(i, 1) for i in id_list]), []
    for current_id in current_ids:
        if current_id in id_list:
            del ids_to_add[current_id]
        else:
            ids_to_delete.append(current_id)
    ids_to_add = ids_to_add.keys()
    # Now ids_to_add is a list of IDs to add, and ids_to_delete is a list of IDs to delete.
    if not ids_to_delete and not ids_to_add:
        return False # No change
    rel = rel_field.rel.to
    m2m_table = rel_field.get_m2m_db_table(self._meta)
    cursor = db.db.cursor()
    this_id = getattr(self, self._meta.pk.name)
    if ids_to_delete:
        sql = "DELETE FROM %s WHERE %s_id = %%s AND %s_id IN (%s)" % (m2m_table, self._meta.object_name.lower(), rel.object_name.lower(), ','.join(map(str, ids_to_delete)))
        cursor.execute(sql, [this_id])
    if ids_to_add:
        sql = "INSERT INTO %s (%s_id, %s_id) VALUES (%%s, %%s)" % (m2m_table, self._meta.object_name.lower(), rel.object_name.lower())
        cursor.executemany(sql, [(this_id, i) for i in ids_to_add])
    db.db.commit()
    try:
        delattr(self, '_%s_cache' % rel_field.name) # clear cache, if it exists
    except AttributeError:
        pass
    return True

# Handles related-object retrieval.
# Examples: Poll.get_choice(), Poll.get_choice_list(), Poll.get_choice_count()
def method_get_related(method_name, rel_mod, rel_field, self, **kwargs):
    kwargs['%s__exact' % rel_field.name] = getattr(self, rel_field.rel.field_name)
    kwargs.update(rel_field.rel.lookup_overrides)
    return getattr(rel_mod, method_name)(**kwargs)

# Handles adding related objects.
# Example: Poll.add_choice()
def method_add_related(rel_obj, rel_mod, rel_field, self, *args, **kwargs):
    init_kwargs = dict(zip([f.name for f in rel_obj.fields if f != rel_field and not isinstance(f, AutoField)], args))
    init_kwargs.update(kwargs)
    for f in rel_obj.fields:
        if isinstance(f, AutoField):
            init_kwargs[f.name] = None
    init_kwargs[rel_field.name] = getattr(self, rel_field.rel.field_name)
    obj = rel_mod.Klass(**init_kwargs)
    obj.save()
    return obj

# Handles related many-to-many object retrieval.
# Examples: Album.get_song(), Album.get_song_list(), Album.get_song_count()
def method_get_related_many_to_many(method_name, rel_mod, rel_field, self, **kwargs):
    kwargs['%s__id__exact' % rel_field.name] = self.id
    return getattr(rel_mod, method_name)(**kwargs)

# Handles setting many-to-many related objects.
# Example: Album.set_songs()
def method_set_related_many_to_many(rel_opts, rel_field, self, id_list):
    id_list = map(int, id_list) # normalize to integers
    rel = rel_field.rel.to
    m2m_table = rel_field.get_m2m_db_table(rel_opts)
    this_id = getattr(self, self._meta.pk.name)
    cursor = db.db.cursor()
    cursor.execute("DELETE FROM %s WHERE %s_id = %%s" % (m2m_table, rel.object_name.lower()), [this_id])
    if rel_field.rel.orderable:
        sql = "INSERT INTO %s (%s_id, %s_id, _order) VALUES (%%s, %%s, %%s)" % (m2m_table, rel.object_name.lower(), rel_opts.object_name.lower())
        cursor.executemany(sql, [(this_id, j, i) for i, j in enumerate(id_list)])
    else:
        sql = "INSERT INTO %s (%s_id, %s_id) VALUES (%%s, %%s)" % (m2m_table, rel.object_name.lower(), rel_opts.object_name.lower())
        cursor.executemany(sql, [(this_id, i) for i in id_list])
    db.db.commit()

# ORDERING METHODS #########################

def method_set_order(ordered_obj, self, id_list):
    cursor = db.db.cursor()
    # Example: "UPDATE poll_choices SET _order = %s WHERE poll_id = %s AND id = %s"
    sql = "UPDATE %s SET _order = %%s WHERE %s = %%s AND %s = %%s" % (ordered_obj.db_table, ordered_obj.order_with_respect_to.name, ordered_obj.pk.name)
    rel_val = getattr(self, ordered_obj.order_with_respect_to.rel.field_name)
    cursor.executemany(sql, [(i, rel_val, j) for i, j in enumerate(id_list)])
    db.db.commit()

def method_get_order(ordered_obj, self):
    cursor = db.db.cursor()
    # Example: "SELECT id FROM poll_choices WHERE poll_id = %s ORDER BY _order"
    sql = "SELECT %s FROM %s WHERE %s = %%s ORDER BY _order" % (ordered_obj.pk.name, ordered_obj.db_table, ordered_obj.order_with_respect_to.name)
    rel_val = getattr(self, ordered_obj.order_with_respect_to.rel.field_name)
    cursor.execute(sql, [rel_val])
    return [r[0] for r in cursor.fetchall()]

# DATE-RELATED METHODS #####################

def method_get_next_or_previous(get_object_func, field, is_next, self, **kwargs):
    kwargs.setdefault('where', []).append('%s %s %%s' % (field.name, (is_next and '>' or '<')))
    kwargs.setdefault('params', []).append(str(getattr(self, field.name)))
    kwargs['order_by'] = ((field.name, (is_next and 'ASC' or 'DESC')),)
    kwargs['limit'] = 1
    return get_object_func(**kwargs)

# FILE-RELATED METHODS #####################

def method_get_file_filename(field, self):
    return os.path.join(settings.MEDIA_ROOT, getattr(self, field.name))

def method_get_file_url(field, self):
    if getattr(self, field.name): # value is not blank
        import urlparse
        return urlparse.urljoin(settings.MEDIA_URL, getattr(self, field.name))
    return ''

def method_get_file_size(field, self):
    return os.path.getsize(method_get_file_filename(field, self))

def method_save_file(field, self, filename, raw_contents):
    directory = field.get_directory_name()
    try: # Create the date-based directory if it doesn't exist.
        os.makedirs(os.path.join(settings.MEDIA_ROOT, directory))
    except OSError: # Directory probably already exists.
        pass
    filename = field.get_filename(filename)

    # If the filename already exists, keep adding an underscore to the name of
    # the file until the filename doesn't exist.
    while os.path.exists(os.path.join(settings.MEDIA_ROOT, filename)):
        try:
            dot_index = filename.rindex('.')
        except ValueError: # filename has no dot
            filename += '_'
        else:
            filename = filename[:dot_index] + '_' + filename[dot_index:]

    # Write the file to disk.
    setattr(self, field.name, filename)
    fp = open(getattr(self, 'get_%s_filename' % field.name)(), 'w')
    fp.write(raw_contents)
    fp.close()

    # Save the width and/or height, if applicable.
    if isinstance(field, ImageField) and (field.width_field or field.height_field):
        from django.utils.images import get_image_dimensions
        width, height = get_image_dimensions(getattr(self, 'get_%s_filename' % field.name)())
        if field.width_field:
            setattr(self, field.width_field, width)
        if field.height_field:
            setattr(self, field.height_field, height)

    # Save the object, because it has changed.
    self.save()

# IMAGE FIELD METHODS ######################

def method_get_image_width(field, self):
    return _get_image_dimensions(field, self)[0]

def method_get_image_height(field, self):
    return _get_image_dimensions(field, self)[1]

def _get_image_dimensions(field, self):
    cachename = "__%s_dimensions_cache" % field.name
    if not hasattr(self, cachename):
        from django.utils.images import get_image_dimensions
        fname = getattr(self, "get_%s_filename" % field.name)()
        setattr(self, cachename, get_image_dimensions(fname))
    return getattr(self, cachename)

##############################################
# HELPER FUNCTIONS (CURRIED MODEL FUNCTIONS) #
##############################################

def get_absolute_url(opts, func, self):
    return settings.ABSOLUTE_URL_OVERRIDES.get('%s.%s' % (opts.app_label, opts.module_name), func)(self)

def _get_where_clause(lookup_type, table_prefix, field_name, value):
    try:
        return '%s%s %s %%s' % (table_prefix, field_name, db.OPERATOR_MAPPING[lookup_type])
    except KeyError:
        pass
    if lookup_type in ('range', 'year'):
        return '%s%s BETWEEN %%s AND %%s' % (table_prefix, field_name)
    elif lookup_type in ('month', 'day'):
        return "EXTRACT('%s' FROM %s%s) = %%s" % (lookup_type, table_prefix, field_name)
    elif lookup_type == 'isnull':
        return "%s%s IS %sNULL" % (table_prefix, field_name, (not value and 'NOT ' or ''))
    raise TypeError, "Got invalid lookup_type: %s" % repr(lookup_type)

def function_get_object(opts, klass, does_not_exist_exception, **kwargs):
    obj_list = function_get_list(opts, klass, **kwargs)
    if len(obj_list) < 1:
        raise does_not_exist_exception, "%s does not exist for %s" % (opts.object_name, kwargs)
    assert len(obj_list) == 1, "get_object() returned more than one %s -- it returned %s! Lookup parameters were %s" % (opts.object_name, len(obj_list), kwargs)
    return obj_list[0]

def _get_cached_row(opts, row, index_start):
    "Helper function that recursively returns an object with cache filled"
    index_end = index_start + len(opts.fields)
    obj = opts.get_model_module().Klass(*row[index_start:index_end])
    for f in opts.fields:
        if f.rel and not f.null:
            rel_obj, index_end = _get_cached_row(f.rel.to, row, index_end)
            setattr(obj, f.rel.get_cache_name(), rel_obj)
    return obj, index_end

def function_get_list(opts, klass, **kwargs):
    # kwargs['select'] is a dictionary, and dictionaries' key order is
    # undefined, so we convert it to a list of tuples internally.
    kwargs['select'] = kwargs.get('select', {}).items()

    cursor = db.db.cursor()
    select, sql, params = function_get_sql_clause(opts, **kwargs)
    cursor.execute("SELECT " + (kwargs.get('distinct') and "DISTINCT " or "") + ",".join(select) + sql, params)
    obj_list = []
    fill_cache = kwargs.get('select_related')
    index_end = len(opts.fields)
    for row in cursor.fetchall():
        if fill_cache:
            obj, index_end = _get_cached_row(opts, row, 0)
        else:
            obj = klass(*row[:index_end])
        for i, k in enumerate(kwargs['select']):
            setattr(obj, k[0], row[index_end+i])
        obj_list.append(obj)
    return obj_list

def function_get_iterator(opts, klass, **kwargs):
    # kwargs['select'] is a dictionary, and dictionaries' key order is
    # undefined, so we convert it to a list of tuples internally.
    kwargs['select'] = kwargs.get('select', {}).items()

    cursor = db.db.cursor()
    select, sql, params = function_get_sql_clause(opts, **kwargs)
    cursor.execute("SELECT " + (kwargs.get('distinct') and "DISTINCT " or "") + ",".join(select) + sql, params)
    fill_cache = kwargs.get('select_related')
    index_end = len(opts.fields)
    while 1:
        rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
        if not rows:
            raise StopIteration
        for row in rows:
            if fill_cache:
                obj, index_end = _get_cached_row(opts, row, 0)
            else:
                obj = klass(*row[:index_end])
            for i, k in enumerate(kwargs['select']):
                setattr(obj, k[0], row[index_end+i])
            yield obj

def function_get_count(opts, **kwargs):
    kwargs['order_by'] = []
    kwargs['offset'] = None
    kwargs['limit'] = None
    kwargs['select_related'] = False
    _, sql, params = function_get_sql_clause(opts, **kwargs)
    cursor = db.db.cursor()
    cursor.execute("SELECT COUNT(*)" + sql, params)
    return cursor.fetchone()[0]

def _fill_table_cache(opts, select, tables, where, old_prefix, cache_tables_seen):
    """
    Helper function that recursively populates the select, tables and where (in
    place) for fill-cache queries.
    """
    for f in opts.fields:
        if f.rel and not f.null:
            db_table = f.rel.to.db_table
            if db_table not in cache_tables_seen:
                tables.append(db_table)
            else: # The table was already seen, so give it a table alias.
                new_prefix = '%s%s' % (db_table, len(cache_tables_seen))
                tables.append('%s %s' % (db_table, new_prefix))
                db_table = new_prefix
            cache_tables_seen.append(db_table)
            where.append('%s.%s = %s.%s' % (old_prefix, f.name, db_table, f.rel.field_name))
            select.extend(['%s.%s' % (db_table, f2.name) for f2 in f.rel.to.fields])
            _fill_table_cache(f.rel.to, select, tables, where, db_table, cache_tables_seen)

def _throw_bad_kwarg_error(kwarg):
    # Helper function to remove redundancy.
    raise TypeError, "got unexpected keyword argument '%s'" % kwarg

def _parse_lookup(kwarg_items, opts, table_count=0):
    # Helper function that handles converting API kwargs (e.g.
    # "name__exact": "tom") to SQL.

    # Note that there is a distinction between where and join_where. The latter
    # is specifically a list of where clauses to use for JOINs. This
    # distinction is necessary because of support for "_or".

    # table_count is used to ensure table aliases are unique.
    tables, join_where, where, params = [], [], [], []
    for kwarg, kwarg_value in kwarg_items:
        if kwarg in ('order_by', 'limit', 'offset', 'select_related', 'distinct', 'select', 'tables', 'where', 'params'):
            continue
        if kwarg_value is None:
            continue
        if kwarg == '_or':
            for val in kwarg_value:
                tables2, join_where2, where2, params2, table_count = _parse_lookup(val, opts, table_count)
                tables.extend(tables2)
                join_where.extend(join_where2)
                where.append('(%s)' % ' OR '.join(where2))
                params.extend(params2)
            continue
        lookup_list = kwarg.split(LOOKUP_SEPARATOR)
        if len(lookup_list) == 1:
            _throw_bad_kwarg_error(kwarg)
        lookup_type = lookup_list.pop()
        current_opts = opts # We'll be overwriting this, so keep a reference to the original opts.
        current_table_alias = current_opts.db_table
        param_required = False
        while lookup_list or param_required:
            table_count += 1
            try:
                # "current" is a piece of the lookup list. For example, in
                # choices.get_list(poll__sites__id__exact=5), lookup_list is
                # ["polls", "sites", "id"], and the first current is "polls".
                try:
                    current = lookup_list.pop(0)
                except IndexError:
                    # If we're here, lookup_list is empty but param_required
                    # is set to True, which means the kwarg was bad.
                    # Example: choices.get_list(poll__exact='foo')
                    _throw_bad_kwarg_error(kwarg)
                # Try many-to-many relationships first...
                for f in current_opts.many_to_many:
                    if f.name == current:
                        rel_table_alias = 't%s' % table_count
                        table_count += 1
                        tables.append('%s %s' % (f.get_m2m_db_table(current_opts), rel_table_alias))
                        join_where.append('%s.%s = %s.%s_id' % (current_table_alias, current_opts.pk.name,
                            rel_table_alias, current_opts.object_name.lower()))
                        # Optimization: In the case of primary-key lookups, we
                        # don't have to do an extra join.
                        if lookup_list and lookup_list[0] == f.rel.to.pk.name and lookup_type == 'exact':
                            where.append(_get_where_clause(lookup_type, rel_table_alias+'.',
                                f.rel.to.object_name.lower()+'_id', kwarg_value))
                            params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                            lookup_list.pop()
                            param_required = False
                        else:
                            new_table_alias = 't%s' % table_count
                            tables.append('%s %s' % (f.rel.to.db_table, new_table_alias))
                            join_where.append('%s.%s_id = %s.%s' % (rel_table_alias, f.rel.to.object_name.lower(),
                                new_table_alias, f.rel.to.pk.name))
                            current_table_alias = new_table_alias
                            param_required = True
                        current_opts = f.rel.to
                        raise StopIteration
                for f in current_opts.fields:
                    # Try many-to-one relationships...
                    if f.rel and f.rel.name == current:
                        # Optimization: In the case of primary-key lookups, we
                        # don't have to do an extra join.
                        if lookup_list and lookup_list[0] == f.rel.to.pk.name and lookup_type == 'exact':
                            where.append(_get_where_clause(lookup_type, current_table_alias+'.', f.name, kwarg_value))
                            params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                            lookup_list.pop()
                            param_required = False
                        else:
                            new_table_alias = 't%s' % table_count
                            tables.append('%s %s' % (f.rel.to.db_table, new_table_alias))
                            join_where.append('%s.%s = %s.%s' % (current_table_alias, f.name, new_table_alias, f.rel.to.pk.name))
                            current_table_alias = new_table_alias
                            param_required = True
                        current_opts = f.rel.to
                        raise StopIteration
                    # Try direct field-name lookups...
                    if f.name == current:
                        where.append(_get_where_clause(lookup_type, current_table_alias+'.', current, kwarg_value))
                        params.extend(f.get_db_prep_lookup(lookup_type, kwarg_value))
                        param_required = False
                        raise StopIteration
                # If we haven't hit StopIteration at this point, "current" must be
                # an invalid lookup, so raise an exception.
                _throw_bad_kwarg_error(kwarg)
            except StopIteration:
                continue
    return tables, join_where, where, params, table_count

def function_get_sql_clause(opts, **kwargs):
    select = ["%s.%s" % (opts.db_table, f.name) for f in opts.fields]
    tables = [opts.db_table] + (kwargs.get('tables') and kwargs['tables'][:] or [])
    where = kwargs.get('where') and kwargs['where'][:] or []
    params = kwargs.get('params') and kwargs['params'][:] or []

    # Convert the kwargs into SQL.
    tables2, join_where2, where2, params2, _ = _parse_lookup(kwargs.items(), opts)
    tables.extend(tables2)
    where.extend(join_where2 + where2)
    params.extend(params2)

    # Add any additional constraints from the "where_constraints" parameter.
    where.extend(opts.where_constraints)

    # Add additional tables and WHERE clauses based on select_related.
    if kwargs.get('select_related') is True:
        _fill_table_cache(opts, select, tables, where, opts.db_table, [opts.db_table])

    # Add any additional SELECTs passed in via kwargs.
    if kwargs.get('select', False):
        select.extend(['(%s) AS %s' % (s[1], s[0]) for s in kwargs['select']])

    # ORDER BY clause
    order_by = []
    for i, j in kwargs.get('order_by', opts.ordering):
        if j == "RANDOM":
            order_by.append("RANDOM()")
        else:
            # Append the database table as a column prefix if it wasn't given,
            # and if the requested column isn't a custom SELECT.
            if "." not in i and i not in [k[0] for k in kwargs.get('select', [])]:
                order_by.append("%s.%s %s" % (opts.db_table, i, j))
            else:
                order_by.append("%s %s" % (i, j))
    order_by = ", ".join(order_by)

    # LIMIT and OFFSET clauses
    if kwargs.get('limit') is not None:
        limit_sql = " LIMIT %s " % kwargs['limit']
        if kwargs.get('offset') is not None and kwargs['offset'] != 0:
            limit_sql += "OFFSET %s " % kwargs['offset']
    else:
        limit_sql = ""

    return select, " FROM " + ",".join(tables) + (where and " WHERE " + " AND ".join(where) or "") + (order_by and " ORDER BY " + order_by or "") + limit_sql, params

def function_get_in_bulk(opts, klass, *args, **kwargs):
    id_list = args and args[0] or kwargs['id_list']
    assert id_list != [], "get_in_bulk() cannot be passed an empty list."
    kwargs['where'] = ["%s.id IN (%s)" % (opts.db_table, ",".join(map(str, id_list)))]
    obj_list = function_get_list(opts, klass, **kwargs)
    return dict([(o.id, o) for o in obj_list])

def function_get_latest(opts, klass, does_not_exist_exception, **kwargs):
    kwargs['order_by'] = ((opts.get_latest_by, "DESC"),)
    kwargs['limit'] = 1
    return function_get_object(opts, klass, does_not_exist_exception, **kwargs)

def function_get_date_list(opts, field, *args, **kwargs):
    kind = args and args[0] or kwargs['kind']
    assert kind in ("month", "year", "day"), "'kind' must be one of 'year', 'month' or 'day'."
    order = 'ASC'
    if kwargs.has_key('_order'):
        order = kwargs['_order']
        del kwargs['_order']
    assert order in ('ASC', 'DESC'), "'order' must be either 'ASC' or 'DESC'"
    kwargs['order_by'] = [] # Clear this because it'll mess things up otherwise.
    if field.null:
        kwargs.setdefault('where', []).append('%s.%s IS NOT NULL' % (opts.db_table, field.name))
    select, sql, params = function_get_sql_clause(opts, **kwargs)
    sql = "SELECT DATE_TRUNC(%%s, %s.%s) %s GROUP BY 1 ORDER BY 1 %s" % (opts.db_table, field.name, sql, order)
    cursor = db.db.cursor()
    cursor.execute(sql, [kind] + params)
    return [row[0] for row in cursor.fetchall()]

###################################
# HELPER FUNCTIONS (MANIPULATORS) #
###################################

def get_manipulator(opts, klass, extra_methods, add=False, change=False):
    "Returns the custom Manipulator (either add or change) for the given opts."
    assert (add == False or change == False) and add != change, "get_manipulator() can be passed add=True or change=True, but not both"
    man = types.ClassType('%sManipulator%s' % (opts.object_name, add and 'Add' or 'Change'), (formfields.Manipulator,), {})
    man.__module__ = MODEL_PREFIX + '.' + opts.module_name # Set this explicitly, as above.
    man.__init__ = curry(manipulator_init, opts, add, change)
    man.save = curry(manipulator_save, opts, klass, add, change)
    for field_name_list in opts.unique_together:
        setattr(man, 'isUnique%s' % '_'.join(field_name_list), curry(manipulator_validator_unique_together, field_name_list, opts))
    for f in opts.fields:
        if f.unique_for_date:
            setattr(man, 'isUnique%sFor%s' % (f.name, f.unique_for_date), curry(manipulator_validator_unique_for_date, f, opts.get_field(f.unique_for_date), opts, 'date'))
        if f.unique_for_month:
            setattr(man, 'isUnique%sFor%s' % (f.name, f.unique_for_month), curry(manipulator_validator_unique_for_date, f, opts.get_field(f.unique_for_month), opts, 'month'))
        if f.unique_for_year:
            setattr(man, 'isUnique%sFor%s' % (f.name, f.unique_for_year), curry(manipulator_validator_unique_for_date, f, opts.get_field(f.unique_for_year), opts, 'year'))
    for k, v in extra_methods.items():
        setattr(man, k, v)
    return man

def manipulator_init(opts, add, change, self, obj_key=None):
    if change:
        assert obj_key is not None, "ChangeManipulator.__init__() must be passed obj_key parameter."
        self.obj_key = obj_key
        try:
            self.original_object = opts.get_model_module().get_object(**{'%s__exact' % opts.pk.name: obj_key})
        except ObjectDoesNotExist:
            # If the object doesn't exist, this might be a manipulator for a
            # one-to-one related object that hasn't created its subobject yet.
            # For example, this might be a Restaurant for a Place that doesn't
            # yet have restaurant information.
            if opts.one_to_one_field:
                # Sanity check -- Make sure the "parent" object exists.
                # For example, make sure the Place exists for the Restaurant.
                # Let the ObjectDoesNotExist exception propogate up.
                lookup_kwargs = opts.one_to_one_field.rel.limit_choices_to
                lookup_kwargs['%s__exact' % opts.one_to_one_field.rel.field_name] = obj_key
                _ = opts.one_to_one_field.rel.to.get_model_module().get_object(**lookup_kwargs)
                params = dict([(f.name, f.get_default()) for f in opts.fields])
                params[opts.pk.name] = obj_key
                self.original_object = opts.get_model_module().Klass(**params)
            else:
                raise
    self.fields = []
    for f in opts.fields + opts.many_to_many:
        if f.editable and (not f.rel or not f.rel.edit_inline):
            self.fields.extend(f.get_manipulator_fields(opts, self, change))

    # Add fields for related objects.
    for rel_opts, rel_field in opts.get_inline_related_objects():
        if change:
            count = getattr(self.original_object, 'get_%s_count' % opts.get_rel_object_method_name(rel_opts, rel_field))()
            count += rel_field.rel.num_extra_on_change
            if rel_field.rel.min_num_in_admin:
                count = max(count, rel_field.rel.min_num_in_admin)
            if rel_field.rel.max_num_in_admin:
                count = min(count, rel_field.rel.max_num_in_admin)
        else:
            count = rel_field.rel.num_in_admin
        for f in rel_opts.fields + rel_opts.many_to_many:
            if f.editable and f != rel_field and (not f.primary_key or (f.primary_key and change)):
                for i in range(count):
                    self.fields.extend(f.get_manipulator_fields(rel_opts, self, change, name_prefix='%s.%d.' % (rel_opts.object_name.lower(), i), rel=True))

    # Add field for ordering.
    if change and opts.get_ordered_objects():
        self.fields.append(formfields.CommaSeparatedIntegerField(field_name="order_"))

def manipulator_save(opts, klass, add, change, self, new_data):
    from django.utils.datastructures import DotExpandedDict
    params = {}
    for f in opts.fields:
        # Fields with auto_now_add are another special case; they should keep
        # their original value in the change stage.
        if change and getattr(f, 'auto_now_add', False):
            params[f.name] = getattr(self.original_object, f.name)
        else:
            params[f.name] = f.get_manipulator_new_data(new_data)

    if change:
        params[opts.pk.name] = self.obj_key

    # First, save the basic object itself.
    new_object = klass(**params)
    new_object.save()

    # Now that the object's been saved, save any uploaded files.
    for f in opts.fields:
        if isinstance(f, FileField):
            f.save_file(new_data, new_object, change and self.original_object or None, change, rel=False)

    # Calculate which primary fields have changed.
    if change:
        self.fields_added, self.fields_changed, self.fields_deleted = [], [], []
        for f in opts.fields:
            if not f.primary_key and str(getattr(self.original_object, f.name)) != str(getattr(new_object, f.name)):
                self.fields_changed.append(f.verbose_name)

    # Save many-to-many objects. Example: Poll.set_sites()
    for f in opts.many_to_many:
        if not f.rel.edit_inline:
            was_changed = getattr(new_object, 'set_%s' % f.name)(new_data.getlist(f.name))
            if change and was_changed:
                self.fields_changed.append(f.verbose_name)

    # Save many-to-one objects. Example: Add the Choice objects for a Poll.
    for rel_opts, rel_field in opts.get_inline_related_objects():
        # Create obj_list, which is a DotExpandedDict such as this:
        # [('0', {'id': ['940'], 'choice': ['This is the first choice']}),
        #  ('1', {'id': ['941'], 'choice': ['This is the second choice']}),
        #  ('2', {'id': [''], 'choice': ['']})]
        obj_list = DotExpandedDict(new_data.data)[rel_opts.object_name.lower()].items()
        obj_list.sort(lambda x, y: cmp(int(x[0]), int(y[0])))
        params = {}

        # For each related item...
        for _, rel_new_data in obj_list:

            # Keep track of which core=True fields were provided.
            # If all core fields were given, the related object will be saved.
            # If none of the core fields were given, the object will be deleted.
            # If some, but not all, of the fields were given, the validator would
            # have caught that.
            all_cores_given, all_cores_blank = True, True

            # Get a reference to the old object. We'll use it to compare the
            # old to the new, to see which fields have changed.
            if change:
                old_rel_obj = None
                if rel_new_data[rel_opts.pk.name][0]:
                    try:
                        old_rel_obj = getattr(self.original_object, 'get_%s' % opts.get_rel_object_method_name(rel_opts, rel_field))(**{'%s__exact' % rel_opts.pk.name: rel_new_data[rel_opts.pk.name][0]})
                    except ObjectDoesNotExist:
                        pass

            for f in rel_opts.fields:
                if f.core and not isinstance(f, FileField) and f.get_manipulator_new_data(rel_new_data, rel=True) in (None, ''):
                    all_cores_given = False
                elif f.core and not isinstance(f, FileField) and f.get_manipulator_new_data(rel_new_data, rel=True) not in (None, ''):
                    all_cores_blank = False
                # If this field isn't editable, give it the same value it had
                # previously, according to the given ID. If the ID wasn't
                # given, use a default value. FileFields are also a special
                # case, because they'll be dealt with later.
                if change and (isinstance(f, FileField) or not f.editable):
                    if rel_new_data.get(rel_opts.pk.name, False) and rel_new_data[rel_opts.pk.name][0]:
                        params[f.name] = getattr(old_rel_obj, f.name)
                    else:
                        params[f.name] = f.get_default()
                elif f == rel_field:
                    params[f.name] = getattr(new_object, rel_field.rel.field_name)
                elif add and isinstance(f, AutoField):
                    params[f.name] = None
                else:
                    params[f.name] = f.get_manipulator_new_data(rel_new_data, rel=True)
                # Related links are a special case, because we have to
                # manually set the "content_type_id" field.
                if opts.has_related_links and rel_opts.module_name == 'relatedlinks':
                    contenttypes_mod = get_module('core', 'contenttypes')
                    params['content_type_id'] = contenttypes_mod.get_object(package__label__exact=opts.app_label, python_module_name__exact=opts.module_name).id
                    params['object_id'] = new_object.id

            # Create the related item.
            new_rel_obj = rel_opts.get_model_module().Klass(**params)

            # If all the core fields were provided (non-empty), save the item.
            if all_cores_given:
                new_rel_obj.save()

                # Save any uploaded files.
                for f in rel_opts.fields:
                    if isinstance(f, FileField) and rel_new_data.get(f.name, False):
                        f.save_file(rel_new_data, new_rel_obj, change and old_rel_obj or None, change, rel=True)

                # Calculate whether any fields have changed.
                if change:
                    if not old_rel_obj: # This object didn't exist before.
                        self.fields_added.append('%s "%r"' % (rel_opts.verbose_name, new_rel_obj))
                    else:
                        for f in rel_opts.fields:
                            if not f.primary_key and f != rel_field and str(getattr(old_rel_obj, f.name)) != str(getattr(new_rel_obj, f.name)):
                                self.fields_changed.append('%s for %s "%r"' % (f.verbose_name, rel_opts.verbose_name, new_rel_obj))

                # Save many-to-many objects.
                for f in rel_opts.many_to_many:
                    if not f.rel.edit_inline:
                        was_changed = getattr(new_rel_obj, 'set_%s' % f.name)(rel_new_data[f.name])
                        if change and was_changed:
                            self.fields_changed.append('%s for %s "%s"' % (f.verbose_name, rel_opts.verbose_name, new_rel_obj))

            # If, in the change stage, all of the core fields were blank and
            # the primary key (ID) was provided, delete the item.
            if change and all_cores_blank and rel_new_data.has_key(rel_opts.pk.name) and rel_new_data[rel_opts.pk.name][0]:
                new_rel_obj.delete()
                self.fields_deleted.append('%s "%r"' % (rel_opts.verbose_name, old_rel_obj))

    # Save the order, if applicable.
    if change and opts.get_ordered_objects():
        order = new_data['order_'] and map(int, new_data['order_'].split(',')) or []
        for rel_opts in opts.get_ordered_objects():
            getattr(new_object, 'set_%s_order' % rel_opts.object_name.lower())(order)
    return new_object

def manipulator_validator_unique(f, opts, self, field_data, all_data):
    "Validates that the value is unique for this field."
    try:
        old_obj = opts.get_model_module().get_object(**{'%s__exact' % f.name: field_data})
    except ObjectDoesNotExist:
        return
    if hasattr(self, 'original_object') and getattr(self.original_object, opts.pk.name) == getattr(old_obj, opts.pk.name):
        return
    raise validators.ValidationError, "%s with this %s already exists." % (capfirst(opts.verbose_name), f.verbose_name)

def manipulator_validator_unique_together(field_name_list, opts, self, field_data, all_data):
    from django.utils.text import get_text_list
    field_list = [opts.get_field(field_name) for field_name in field_name_list]
    kwargs = {'%s__iexact' % field_name_list[0]: field_data}
    for f in field_list[1:]:
        field_val = all_data.get(f.name, None)
        if field_val is None:
            # This will be caught by another validator, assuming the field
            # doesn't have blank=True.
            return
        kwargs['%s__iexact' % f.name] = field_val
    mod = opts.get_model_module()
    try:
        old_obj = mod.get_object(**kwargs)
    except ObjectDoesNotExist:
        return
    if hasattr(self, 'original_object') and getattr(self.original_object, opts.pk.name) == getattr(old_obj, opts.pk.name):
        pass
    else:
        raise validators.ValidationError, "%s with this %s already exists for the given %s." % \
            (capfirst(opts.verbose_name), field_list[0].verbose_name, get_text_list(field_name_list[1:], 'and'))

def manipulator_validator_unique_for_date(from_field, date_field, opts, lookup_type, self, field_data, all_data):
    date_str = all_data.get(date_field.get_manipulator_field_names('')[0], None)
    mod = opts.get_model_module()
    date_val = formfields.DateField.html2python(date_str)
    if date_val is None:
        return # Date was invalid. This will be caught by another validator.
    lookup_kwargs = {'%s__iexact' % from_field.name: field_data, '%s__year' % date_field.name: date_val.year}
    if lookup_type in ('month', 'date'):
        lookup_kwargs['%s__month' % date_field.name] = date_val.month
    if lookup_type == 'date':
        lookup_kwargs['%s__day' % date_field.name] = date_val.day
    try:
        old_obj = mod.get_object(**lookup_kwargs)
    except ObjectDoesNotExist:
        return
    else:
        if hasattr(self, 'original_object') and getattr(self.original_object, opts.pk.name) == getattr(old_obj, opts.pk.name):
            pass
        else:
            format_string = (lookup_type == 'date') and '%B %d, %Y' or '%B %Y'
            raise validators.ValidationError, "Please enter a different %s. The one you entered is already being used for %s." % \
                (from_field.verbose_name, date_val.strftime(format_string))

def manipulator_valid_rel_key(f, self, field_data, all_data):
    "Validates that the value is a valid foreign key"
    mod = f.rel.to.get_model_module()
    try:
        mod.get_object(**{'id__iexact': field_data})
    except ObjectDoesNotExist:
        raise validators.ValidationError, "Please enter a valid %s." % f.verbose_name

####################
# FIELDS           #
####################

class Field(object):

    # Designates whether empty strings fundamentally are allowed at the
    # database level.
    empty_strings_allowed = True

    def __init__(self, name, verbose_name, primary_key=False,
        maxlength=None, unique=False, blank=False, null=False, db_index=None,
        core=False, rel=None, default=NOT_PROVIDED, editable=True,
        prepopulate_from=None, unique_for_date=None, unique_for_month=None,
        unique_for_year=None, validator_list=None, choices=None, radio_admin=None,
        help_text=''):
        self.name, self.verbose_name = name, verbose_name
        self.primary_key = primary_key
        self.maxlength, self.unique = maxlength, unique
        self.blank, self.null = blank, null
        self.core, self.rel, self.default = core, rel, default
        self.editable = editable
        self.validator_list = validator_list or []
        self.prepopulate_from = prepopulate_from
        self.unique_for_date, self.unique_for_month = unique_for_date, unique_for_month
        self.unique_for_year = unique_for_year
        self.choices = choices or []
        self.radio_admin = radio_admin
        self.help_text = help_text
        if rel and isinstance(rel, ManyToMany):
            self.help_text += ' Hold down "Control", or "Command" on a Mac, to select more than one.'

        # Set db_index to True if the field has a relationship and doesn't explicitly set db_index.
        if db_index is None:
            if isinstance(rel, OneToOne) or isinstance(rel, ManyToOne):
                self.db_index = True
            else:
                self.db_index = False
        else:
            self.db_index = db_index

    def pre_save(self, obj, value, add):
        """
        Hook for altering the object obj based on the value of this field and
        and on the add/change status.
        """
        pass

    def get_db_prep_save(self, value, add):
        "Returns field's value prepared for saving into a database."
        return value

    def get_db_prep_lookup(self, lookup_type, value):
        "Returns field's value prepared for database lookup."
        if lookup_type in ('exact', 'gt', 'gte', 'lt', 'lte', 'ne', 'month', 'day'):
            return [value]
        elif lookup_type == 'range':
            return value
        elif lookup_type == 'year':
            return ['%s-01-01' % value, '%s-12-31' % value]
        elif lookup_type in ('contains', 'icontains'):
            return ["%%%s%%" % prep_for_like_query(value)]
        elif lookup_type == 'iexact':
            return [prep_for_like_query(value)]
        elif lookup_type == 'startswith':
            return ["%s%%" % prep_for_like_query(value)]
        elif lookup_type == 'endswith':
            return ["%%%s" % prep_for_like_query(value)]
        elif lookup_type == 'isnull':
            return []
        raise TypeError, "Field has invalid lookup: %s" % lookup_type

    def get_m2m_db_table(self, original_opts):
        "Returns the name of the DB table for this field's relationship."
        return '%s_%s' % (original_opts.db_table, self.name)

    def has_default(self):
        "Returns a boolean of whether this field has a default value."
        return self.default != NOT_PROVIDED

    def get_default(self):
        "Returns the default value for this field."
        if self.default != NOT_PROVIDED:
            if hasattr(self.default, '__get_value__'):
                return self.default.__get_value__()
            return self.default
        if self.null:
            return None
        return ""

    def get_manipulator_field_names(self, name_prefix):
        """
        Returns a list of field names that this object adds to the manipulator.
        """
        return [name_prefix + self.name]

    def get_manipulator_fields(self, opts, manipulator, change, name_prefix='', rel=False):
        """
        Returns a list of formfields.FormField instances for this field. It
        calculates the choices at runtime, not at compile time.

        name_prefix is a prefix to prepend to the "field_name" argument.
        rel is a boolean specifying whether this field is in a related context.
        """
        params = {'validator_list': self.validator_list[:]}
        if self.maxlength and not self.choices: # Don't give SelectFields a maxlength parameter.
            params['maxlength'] = self.maxlength
        if isinstance(self.rel, ManyToOne):
            if self.rel.raw_id_admin:
                field_objs = self.get_manipulator_field_objs()
                params['validator_list'].append(curry(manipulator_valid_rel_key, self, manipulator))
            else:
                if self.radio_admin:
                    field_objs = [formfields.RadioSelectField]
                    params['choices'] = self.get_choices(include_blank=self.blank, blank_choice=BLANK_CHOICE_NONE)
                    params['ul_class'] = get_ul_class(self.radio_admin)
                else:
                    if self.null:
                        field_objs = [formfields.NullSelectField]
                    else:
                        field_objs = [formfields.SelectField]
                    params['choices'] = self.get_choices()
        elif self.choices:
            if self.radio_admin:
                field_objs = [formfields.RadioSelectField]
                params['choices'] = self.get_choices(include_blank=self.blank, blank_choice=BLANK_CHOICE_NONE)
                params['ul_class'] = get_ul_class(self.radio_admin)
            else:
                field_objs = [formfields.SelectField]
                params['choices'] = self.get_choices()
        else:
            field_objs = self.get_manipulator_field_objs()

        # Add the "unique" validator(s).
        for field_name_list in opts.unique_together:
            if field_name_list[0] == self.name:
                params['validator_list'].append(getattr(manipulator, 'isUnique%s' % '_'.join(field_name_list)))

        # Add the "unique for..." validator(s).
        if self.unique_for_date:
            params['validator_list'].append(getattr(manipulator, 'isUnique%sFor%s' % (self.name, self.unique_for_date)))
        if self.unique_for_month:
            params['validator_list'].append(getattr(manipulator, 'isUnique%sFor%s' % (self.name, self.unique_for_month)))
        if self.unique_for_year:
            params['validator_list'].append(getattr(manipulator, 'isUnique%sFor%s' % (self.name, self.unique_for_year)))
        if self.unique:
            params['validator_list'].append(curry(manipulator_validator_unique, self, opts, manipulator))

        # Only add is_required=True if the field cannot be blank. Primary keys
        # are a special case, and fields in a related context should set this
        # as False, because they'll be caught by a separate validator --
        # RequiredIfOtherFieldGiven.
        params['is_required'] = not self.blank and not self.primary_key and not rel

        # If this field is in a related context, check whether any other fields
        # in the related object have core=True. If so, add a validator --
        # RequiredIfOtherFieldsGiven -- to this FormField.
        if rel and not self.blank and not isinstance(self, AutoField) and not isinstance(self, FileField):
            # First, get the core fields, if any.
            core_field_names = []
            for f in opts.fields:
                if f.core and f != self:
                    core_field_names.extend(f.get_manipulator_field_names(name_prefix))
            # Now, if there are any, add the validator to this FormField.
            if core_field_names:
                params['validator_list'].append(validators.RequiredIfOtherFieldsGiven(core_field_names, "This field is required."))

        # BooleanFields (CheckboxFields) are a special case. They don't take
        # is_required or validator_list.
        if isinstance(self, BooleanField):
            del params['validator_list'], params['is_required']

        # Finally, add the field_names.
        field_names = self.get_manipulator_field_names(name_prefix)
        return [man(field_name=field_names[i], **params) for i, man in enumerate(field_objs)]

    def get_manipulator_new_data(self, new_data, rel=False):
        """
        Given the full new_data dictionary (from the manipulator), returns this
        field's data.
        """
        if rel:
            return new_data.get(self.name, [self.get_default()])[0]
        else:
            val = new_data.get(self.name, self.get_default())
            if not self.empty_strings_allowed and val == '' and self.null:
                val = None
            return val

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH):
        "Returns a list of tuples used as SelectField choices for this field."
        first_choice = include_blank and blank_choice or []
        if self.choices:
            return first_choice + list(self.choices)
        rel_obj = self.rel.to
        return first_choice + [(getattr(x, rel_obj.pk.name), repr(x)) for x in rel_obj.get_model_module().get_list(**self.rel.limit_choices_to)]

class AutoField(Field):
    empty_strings_allowed = False
    def get_manipulator_fields(self, opts, manipulator, change, name_prefix='', rel=False):
        if not rel:
            return [] # Don't add a FormField unless it's in a related context.
        return Field.get_manipulator_fields(self, opts, manipulator, change, name_prefix, rel)

    def get_manipulator_field_objs(self):
        return [formfields.HiddenField]

    def get_manipulator_new_data(self, new_data, rel=False):
        if not rel:
            return None
        return Field.get_manipulator_new_data(self, new_data, rel)

class BooleanField(Field):
    def __init__(self, name, verbose_name, **kwargs):
        kwargs['blank'] = True
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_field_objs(self):
        return [formfields.CheckboxField]

class CharField(Field):
    def get_manipulator_field_objs(self):
        return [formfields.TextField]

class CommaSeparatedIntegerField(CharField):
    def get_manipulator_field_objs(self):
        return [formfields.CommaSeparatedIntegerField]

class DateField(Field):
    empty_strings_allowed = False
    def __init__(self, name, verbose_name, auto_now=False, auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add = auto_now, auto_now_add
        if auto_now or auto_now_add:
            kwargs['editable'] = False
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_db_prep_lookup(self, lookup_type, value):
        if lookup_type == 'range':
            value = [str(v) for v in value]
        else:
            value = str(value)
        return Field.get_db_prep_lookup(self, lookup_type, value)

    def pre_save(self, obj, value, add):
        if self.auto_now or (self.auto_now_add and add):
            setattr(obj, self.name, datetime.datetime.now())

    def get_db_prep_save(self, value, add):
        # Casts dates into string format for entry into database.
        if value is not None:
            value = value.strftime('%Y-%m-%d')
        return Field.get_db_prep_save(self, value, add)

    def get_manipulator_field_objs(self):
        return [formfields.DateField]

class DateTimeField(DateField):
    def get_db_prep_save(self, value, add):
        # Casts dates into string format for entry into database.
        if value is not None:
            value = value.strftime('%Y-%m-%d %H:%M:%S')
        return Field.get_db_prep_save(self, value, add)

    def get_manipulator_field_objs(self):
        return [formfields.DateField, formfields.TimeField]

    def get_manipulator_field_names(self, name_prefix):
        return [name_prefix + self.name + '_date', name_prefix + self.name + '_time']

    def get_manipulator_new_data(self, new_data, rel=False):
        date_field, time_field = self.get_manipulator_field_names('')
        if rel:
            d = new_data.get(date_field, [None])[0]
            t = new_data.get(time_field, [None])[0]
        else:
            d = new_data.get(date_field, None)
            t = new_data.get(time_field, None)
        if d is not None and t is not None:
            return datetime.datetime.combine(d, t)
        return self.get_default()

class EmailField(Field):
    def get_manipulator_field_objs(self):
        return [formfields.EmailField]

class FileField(Field):
    def __init__(self, name, verbose_name, upload_to='', **kwargs):
        self.upload_to = upload_to
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_fields(self, opts, manipulator, change, name_prefix='', rel=False):
        field_list = Field.get_manipulator_fields(self, opts, manipulator, change, name_prefix, rel)

        if not self.blank:
            if rel:
                # This validator makes sure FileFields work in a related context.
                class RequiredFileField:
                    def __init__(self, other_field_names, other_file_field_name):
                        self.other_field_names = other_field_names
                        self.other_file_field_name = other_file_field_name
                        self.always_test = True
                    def __call__(self, field_data, all_data):
                        if not all_data.get(self.other_file_field_name, False):
                            c = validators.RequiredIfOtherFieldsGiven(self.other_field_names, "This field is required.")
                            c(field_data, all_data)
                # First, get the core fields, if any.
                core_field_names = []
                for f in opts.fields:
                    if f.core and f != self:
                        core_field_names.extend(f.get_manipulator_field_names(name_prefix))
                # Now, if there are any, add the validator to this FormField.
                if core_field_names:
                    field_list[0].validator_list.append(RequiredFileField(core_field_names, field_list[1].field_name))
            else:
                v = validators.RequiredIfOtherFieldNotGiven(field_list[1].field_name, "This field is required.")
                v.always_test = True
                field_list[0].validator_list.append(v)
                field_list[0].is_required = field_list[1].is_required = False

        # If the raw path is passed in, validate it's under the MEDIA_ROOT.
        def isWithinMediaRoot(field_data, all_data):
            f = os.path.abspath(os.path.join(settings.MEDIA_ROOT, field_data))
            if not f.startswith(os.path.normpath(settings.MEDIA_ROOT)):
                raise validators.ValidationError, "Enter a valid filename."
        field_list[1].validator_list.append(isWithinMediaRoot)
        return field_list

    def get_manipulator_field_objs(self):
        return [formfields.FileUploadField, formfields.HiddenField]

    def get_manipulator_field_names(self, name_prefix):
        return [name_prefix + self.name + '_file', name_prefix + self.name]

    def save_file(self, new_data, new_object, original_object, change, rel):
        upload_field_name = self.get_manipulator_field_names('')[0]
        if new_data.get(upload_field_name, False):
            if rel:
                getattr(new_object, 'save_%s_file' % self.name)(new_data[upload_field_name][0]["filename"], new_data[upload_field_name][0]["content"])
            else:
                getattr(new_object, 'save_%s_file' % self.name)(new_data[upload_field_name]["filename"], new_data[upload_field_name]["content"])

    def get_directory_name(self):
        return os.path.normpath(datetime.datetime.now().strftime(self.upload_to))

    def get_filename(self, filename):
        from django.utils.text import get_valid_filename
        f = os.path.join(self.get_directory_name(), get_valid_filename(os.path.basename(filename)))
        return os.path.normpath(f)

class FloatField(Field):
    empty_strings_allowed = False
    def __init__(self, name, verbose_name, max_digits, decimal_places, **kwargs):
        self.max_digits, self.decimal_places = max_digits, decimal_places
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_field_objs(self):
        return [curry(formfields.FloatField, max_digits=self.max_digits, decimal_places=self.decimal_places)]

class ImageField(FileField):
    def __init__(self, name, verbose_name, width_field=None, height_field=None, **kwargs):
        self.width_field, self.height_field = width_field, height_field
        FileField.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_field_objs(self):
        return [formfields.ImageUploadField, formfields.HiddenField]

    def save_file(self, new_data, new_object, original_object, change, rel):
        FileField.save_file(self, new_data, new_object, original_object, change, rel)
        # If the image has height and/or width field(s) and they haven't
        # changed, set the width and/or height field(s) back to their original
        # values.
        if change and (self.width_field or self.height_field):
            if self.width_field:
                setattr(new_object, self.width_field, getattr(original_object, self.width_field))
            if self.height_field:
                setattr(new_object, self.height_field, getattr(original_object, self.height_field))
            new_object.save()

class IntegerField(Field):
    empty_strings_allowed = False
    def get_manipulator_field_objs(self):
        return [formfields.IntegerField]

class IPAddressField(Field):
    def __init__(self, name, verbose_name, **kwargs):
        kwargs['maxlength'] = 15
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_field_objs(self):
        return [formfields.IPAddressField]

class NullBooleanField(Field):
    def __init__(self, name, verbose_name, **kwargs):
        kwargs['null'] = True
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_field_objs(self):
        return [formfields.NullBooleanField]

class PhoneNumberField(IntegerField):
    def get_manipulator_field_objs(self):
        return [formfields.PhoneNumberField]

class PositiveIntegerField(IntegerField):
    def get_manipulator_field_objs(self):
        return [formfields.PositiveIntegerField]

class PositiveSmallIntegerField(IntegerField):
    def get_manipulator_field_objs(self):
        return [formfields.PositiveSmallIntegerField]

class SlugField(Field):
    def __init__(self, name, verbose_name, **kwargs):
        kwargs['maxlength'] = 50
        kwargs.setdefault('validator_list', []).append(validators.isAlphaNumeric)
        # Set db_index=True unless it's been set manually.
        if not kwargs.has_key('db_index'):
            kwargs['db_index'] = True
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_field_objs(self):
        return [formfields.TextField]

class SmallIntegerField(IntegerField):
    def get_manipulator_field_objs(self):
        return [formfields.SmallIntegerField]

class TextField(Field):
    def get_manipulator_field_objs(self):
        return [formfields.LargeTextField]

class TimeField(Field):
    empty_strings_allowed = False
    def __init__(self, name, verbose_name, auto_now=False, auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add  = auto_now, auto_now_add
        if auto_now or auto_now_add:
            kwargs['editable'] = False
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_db_prep_lookup(self, lookup_type, value):
        if lookup_type == 'range':
            value = [str(v) for v in value]
        else:
            value = str(value)
        return Field.get_db_prep_lookup(self, lookup_type, value)

    def pre_save(self, obj, value, add):
        if self.auto_now or (self.auto_now_add and add):
            setattr(obj, self.name, datetime.datetime.now().time())

    def get_db_prep_save(self, value, add):
        # Casts dates into string format for entry into database.
        if value is not None:
            value = value.strftime('%H:%M:%S')
        return Field.get_db_prep_save(self, value, add)

    def get_manipulator_field_objs(self):
        return [formfields.TimeField]

class URLField(Field):
    def __init__(self, name, verbose_name, verify_exists=True, **kwargs):
        if verify_exists:
            kwargs.setdefault('validator_list', []).append(validators.isExistingURL)
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_field_objs(self):
        return [formfields.URLField]

class USStateField(Field):
    def get_manipulator_field_objs(self):
        return [formfields.USStateField]

class XMLField(Field):
    def __init__(self, name, verbose_name, schema_path, **kwargs):
        self.schema_path = schema_path
        Field.__init__(self, name, verbose_name, **kwargs)

    def get_manipulator_field_objs(self):
        return [curry(formfields.XMLLargeTextField, schema_path=self.schema_path)]

class ForeignKey(Field):
    empty_strings_allowed = False
    def __init__(self, to, to_field=None, rel_name=None, **kwargs):
        try:
            to_name = to._meta.object_name.lower()
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            kwargs['name'] = kwargs['name']
            kwargs['verbose_name'] = kwargs['verbose_name']
        else:
            to_field = to_field or to._meta.pk.name
            kwargs['name'] = kwargs.get('name', to_name + '_id')
            kwargs['verbose_name'] = kwargs.get('verbose_name', to._meta.verbose_name)
            rel_name = rel_name or to_name
        kwargs['rel'] = ManyToOne(to, rel_name, to_field,
            num_in_admin=kwargs.pop('num_in_admin', 0),
            min_num_in_admin=kwargs.pop('min_num_in_admin', None),
            max_num_in_admin=kwargs.pop('max_num_in_admin', None),
            num_extra_on_change=kwargs.pop('num_extra_on_change', 1),
            edit_inline=kwargs.pop('edit_inline', False),
            edit_inline_type=kwargs.pop('edit_inline_type', STACKED),
            related_name=kwargs.pop('related_name', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None),
            lookup_overrides=kwargs.pop('lookup_overrides', None),
            raw_id_admin=kwargs.pop('raw_id_admin', False))
        Field.__init__(self, **kwargs)

    def get_manipulator_field_objs(self):
        return [formfields.IntegerField]

class ManyToManyField(Field):
    def __init__(self, to, **kwargs):
        kwargs['name'] = kwargs.get('name', to._meta.module_name)
        kwargs['verbose_name'] = kwargs.get('verbose_name', to._meta.verbose_name_plural)
        kwargs['rel'] = ManyToMany(to, to._meta.object_name.lower() + '_id',
            num_in_admin=kwargs.pop('num_in_admin', 0),
            related_name=kwargs.pop('related_name', None),
            filter_interface=kwargs.pop('filter_interface', None),
            get_choices_from=kwargs.pop('get_choices_from', None),
            limit_choices_to=kwargs.pop('limit_choices_to', None))
        Field.__init__(self, **kwargs)

    def get_manipulator_field_objs(self):
        choices = self.get_choices(include_blank=False)
        return [curry(formfields.SelectMultipleField, size=min(max(len(choices), 5), 15), choices=choices)]

####################
# RELATIONSHIPS    #
####################

class ManyToOne:
    def __init__(self, to, name, field_name, num_in_admin=0, min_num_in_admin=None,
        max_num_in_admin=None, num_extra_on_change=1, edit_inline=False, edit_inline_type=STACKED,
        related_name=None, limit_choices_to=None, lookup_overrides=None, raw_id_admin=False):
        try:
            self.to = to._meta
        except AttributeError: # to._meta doesn't exist, so it must be RECURSIVE_RELATIONSHIP_CONSTANT
            assert to == RECURSIVE_RELATIONSHIP_CONSTANT, "'to' must be either a model or the string '%s'" % RECURSIVE_RELATIONSHIP_CONSTANT
            self.to = to
        self.name, self.field_name = name, field_name
        self.num_in_admin, self.edit_inline = num_in_admin, edit_inline
        self.min_num_in_admin, self.max_num_in_admin = min_num_in_admin, max_num_in_admin
        self.num_extra_on_change = num_extra_on_change
        self.edit_inline_type, self.related_name = edit_inline_type, related_name
        self.limit_choices_to = limit_choices_to or {}
        self.lookup_overrides = lookup_overrides or {}
        self.raw_id_admin = raw_id_admin

    def get_cache_name(self):
        return '_%s_cache' % self.name

    def get_related_field(self):
        "Returns the Field in the 'to' object to which this relationship is tied."
        return self.to.get_field(self.field_name)

class ManyToMany:
    def __init__(self, to, name, num_in_admin=0, related_name=None,
        filter_interface=None, get_choices_from=None, limit_choices_to=None):
        self.to, self.name = to._meta, name
        self.num_in_admin = num_in_admin
        self.related_name = related_name
        self.filter_interface, self.get_choices_from = filter_interface, get_choices_from
        self.limit_choices_to = limit_choices_to or {}
        self.edit_inline = False

class OneToOne(ManyToOne):
    def __init__(self, to, name, field_name, num_in_admin=0, edit_inline=False,
        edit_inline_type=STACKED, related_name=None, limit_choices_to=None, lookup_overrides=None,
        raw_id_admin=False):
        self.to, self.name, self.field_name = to._meta, name, field_name
        self.num_in_admin, self.edit_inline = num_in_admin, edit_inline
        self.edit_inline_type, self.related_name = edit_inline_type, related_name
        self.limit_choices_to = limit_choices_to or {}
        self.lookup_overrides = lookup_overrides or {}
        self.raw_id_admin = raw_id_admin

class Admin:
    def __init__(self, fields, js=None, list_display=None, list_filter=None, date_hierarchy=None,
        save_as=False, ordering=None, search_fields=None, save_on_top=False):
        self.fields = fields
        self.js = js or []
        self.list_display = list_display or ['__repr__']
        self.list_filter = list_filter or []
        self.date_hierarchy = date_hierarchy
        self.save_as, self.ordering = save_as, ordering
        self.search_fields = search_fields or []
        self.save_on_top = save_on_top

    def copy(self):
        return copy.deepcopy(self)
