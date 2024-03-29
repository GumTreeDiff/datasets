from django.conf.urls import patterns, url
from wagtail.wagtailadmin.forms import LoginForm

urlpatterns = patterns('django.contrib.auth.views',
    url(r'^login/$', 'login', {'template_name': 'wagtailadmin/login.html', 'authentication_form': LoginForm}),
    url(r'^logout/$', 'logout', {'next_page': '/admin/login/'}),
)

urlpatterns += patterns('wagtail.wagtailadmin.views',
    url(r'^$', 'home.home', name='wagtailadmin_home'),

    url(r'^failwhale/$', 'home.error_test', name='wagtailadmin_error_test'),

    url(r'^pages/$', 'pages.index', name='wagtailadmin_explore_root'),
    url(r'^pages/(\d+)/$', 'pages.index', name='wagtailadmin_explore'),

    url(r'^pages/new/$', 'pages.select_type', name='wagtailadmin_pages_select_type'),
    url(r'^pages/new/(\w+)/(\w+)/$', 'pages.select_location', name='wagtailadmin_pages_select_location'),
    url(r'^pages/new/(\w+)/(\w+)/(\d+)/$', 'pages.create', name='wagtailadmin_pages_create'),
    url(r'^pages/new/(\w+)/(\w+)/(\d+)/preview/$', 'pages.preview_on_create', name='wagtailadmin_pages_preview_on_create'),
    url(r'^pages/usage/(\w+)/(\w+)/$', 'pages.content_type_use', name='wagtailadmin_pages_type_use'),

    url(r'^pages/(\d+)/edit/$', 'pages.edit', name='wagtailadmin_pages_edit'),
    url(r'^pages/(\d+)/edit/preview/$', 'pages.preview_on_edit', name='wagtailadmin_pages_preview_on_edit'),

    url(r'^pages/preview_placeholder/$', 'pages.preview_placeholder', name='wagtailadmin_pages_preview_placeholder'),

    url(r'^pages/(\d+)/view_draft/$', 'pages.view_draft', name='wagtailadmin_pages_view_draft'),
    url(r'^pages/(\d+)/add_subpage/$', 'pages.add_subpage', name='wagtailadmin_pages_add_subpage'),
    url(r'^pages/(\d+)/delete/$', 'pages.delete', name='wagtailadmin_pages_delete'),
    url(r'^pages/(\d+)/unpublish/$', 'pages.unpublish', name='wagtailadmin_pages_unpublish'),

     url(r'^pages/search/$', 'pages.search', name='wagtailadmin_pages_search'),

    url(r'^pages/(\d+)/move/$', 'pages.move_choose_destination', name='wagtailadmin_pages_move'),
    url(r'^pages/(\d+)/move/(\d+)/$', 'pages.move_choose_destination', name='wagtailadmin_pages_move_choose_destination'),
    url(r'^pages/(\d+)/move/(\d+)/confirm/$', 'pages.move_confirm', name='wagtailadmin_pages_move_confirm'),
    url(r'^pages/(\d+)/set_position/$', 'pages.set_page_position', name='wagtailadmin_pages_set_page_position'),

    url(r'^pages/moderation/(\d+)/approve/$', 'pages.approve_moderation', name='wagtailadmin_pages_approve_moderation'),
    url(r'^pages/moderation/(\d+)/reject/$', 'pages.reject_moderation', name='wagtailadmin_pages_reject_moderation'),
    url(r'^pages/moderation/(\d+)/preview/$', 'pages.preview_for_moderation', name='wagtailadmin_pages_preview_for_moderation'),

    url(r'^choose-page/$', 'chooser.browse', name='wagtailadmin_choose_page'),
    url(r'^choose-page/(\d+)/$', 'chooser.browse', name='wagtailadmin_choose_page_child'),
    url(r'^choose-external-link/$', 'chooser.external_link', name='wagtailadmin_choose_page_external_link'),
    url(r'^choose-email-link/$', 'chooser.email_link', name='wagtailadmin_choose_page_email_link'),

    url(r'^tag-autocomplete/$', 'tags.autocomplete', name='wagtailadmin_tag_autocomplete'),
)
