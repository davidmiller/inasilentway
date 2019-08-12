"""inasilentway URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include

from inasilentway import views

urlpatterns = [
    url(r'^the-admin/', admin.site.urls),
    path('account/', include('django.contrib.auth.urls')),

    url(r'^$', views.HomeView.as_view(), name='home'),

    path('collection/', views.CollectionView.as_view(), name='record-list'),

    # Different views of records - detail, edit, alternative lists
    path('record/<int:pk>/<slug>', views.RecordView.as_view(), name='record'),
    path(
        'record/delete/<int:pk>/',
        views.DeleteRecordView.as_view(),
        name='delete-record'),

    path('genre/<int:pk>/<slug>/', views.GenreView.as_view(), name='genre'),
    path('label/<int:pk>', views.LabelView.as_view(), name='label'),
    path('style/<int:pk>/<slug>/', views.StyleView.as_view(), name='style'),
    path('search/', views.SearchView.as_view(), name='search'),

    path('unplayed/', views.UnplayedView.as_view(), name='unplayed'),
    path('oldest/', views.OldestView.as_view(), name='oldest'),

    # Artist views
    path('artist/<int:pk>/<slug>/', views.ArtistView.as_view(), name='artist'),

    # Last.fm / listening history views
    path('scrobbles/', views.ScrobbleListView.as_view(), name='scrobble-list'),
    path(
        'scrobbles/recently-scrobbled-records/',
        views.RecentlyScrobbledRecordsView.as_view(),
        name='recently-scrobbled-records'
    ),
    path(
        'scrobbles/unlinked/',
        views.UnlinkedScrobbleView.as_view(),
        name='unlinked-scrobbles'),
    path(
        'submit-scrobble/',
        views.SubmitScrobbleView.as_view(),
        name='submit-scrobble'),
    path(
        'load-scrobbles/',
        views.RetrieveScrobblesView.as_view(),
        name='load-scrobbles'
    ),
    path(
        'scrobble-retrieval-error',
        views.ScrobbleRetrievalErroView.as_view(),
        name='scrobble-retrieval-error'
    ),
    path(
        'load-collection/',
        views.RetrieveCollectionView.as_view(),
        name='load-collection'
    ),
    path(
        'collection-loading-error',
        views.CollectionLoadingErroView.as_view(),
        name='collection-loading-error'
    ),
    path(
        'listening-history/',
        views.ListeningHistoryView.as_view(),
        name='listening-history'),
    path(
        'listening-history/<int:year>/',
        views.ListeningHistoryYearView.as_view(),
        name='listening-history-year'),
    path(
        'listening-history/<int:year>/<str:month>',
        views.ListeningHistoryMonthView.as_view(),
        name='listening-history-month'),
    path(
        'top-artists',
        views.TopArtistsView.as_view(),
        name='top-artists'
    ),

]
