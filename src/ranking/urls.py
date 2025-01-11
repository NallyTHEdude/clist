from django.urls import re_path

from ranking import views

app_name = 'ranking'

urlpatterns = [
    re_path(r'^standings/$', views.standings_list, name='standings_list'),
    re_path(r'^standings/action/$', views.standings_action, name='standings_action'),
    re_path(r'^standings/(?P<title_slug>[^/]*)-(?P<contest_id>[0-9]+)/$', views.standings, name='standings'),
    re_path(r'^standings/(?P<contest_id>[0-9]+)/$', views.standings, name='standings_by_id'),
    re_path(r'^standings/(?P<contests_ids>[0-9]+(?:,[0-9]+)+)/$', views.standings, name='standings_by_ids'),
    re_path(r'^standings/(?P<title_slug>[^/]+)/$', views.standings, name='standings_by_slug'),
    re_path(r'^solutions/(?P<sid>[0-9]+)/(?P<problem_key>.*)/$', views.solutions, name='solution'),
    re_path(r'^score-history/(?P<statistic_id>[0-9]+)/$', views.score_history, name='score-history'),
    re_path(r'^score-history/(?P<statistic_ids>[0-9]+(?:,[0-9]+)+)/$', views.score_histories, name='score-histories'),
    re_path(r'^versus/$', views.make_versus, name='make_versus'),
    re_path(r'^versus/(.+/vs/.+)/$', views.versus, name='versus'),
    re_path(r'^virtual-start/$', views.virtual_start, name='virtual_start'),
]
