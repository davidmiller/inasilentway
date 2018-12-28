"""
Views for inasilentway
"""
import collections
import datetime
import random
import time

from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, TemplateView
from django.views.generic.edit import DeleteView, FormView

from inasilentway import forms, lastfm
from inasilentway.models import Record, Artist, Genre, Label, Scrobble, Style


class RecordListView(ListView):
    """
    A base class for lists of records.

    This class is not wired up to urls directly, but provides generic
    sort and random fucnctionality, as well as linking to Django's
    generic ListView.
    """

    model       = Record
    paginate_by = 50

    def redirect_to_random_record(self):
        """
        Redirect to a random record from the queryset for this
        ListView.
        """
        qs = self.get_queryset()
        ids = qs.values_list('id', flat=True)
        record = Record.objects.get(pk=random.choice(ids))
        return redirect(record.get_absolute_url())

    def dispatch(self, *a, **k):
        if self.request.GET.get('redirect', None == 'random'):
            return self.redirect_to_random_record()
        return super().dispatch(*a, **k)

    def get_sort(self):
        sorts = {
            'artist': 'artist__name',
            'title ': 'title',
            'year'  : 'year'
        }

        if self.request.GET.get('sort', None) in sorts:
            sort = sorts[self.request.GET['sort']]
        else:
            sort = 'title'
        return sort

    def get_queryset(self):
        qs = self.model.objects.filter(
            title__isnull=False
        ).order_by(self.get_sort()).distinct()
        self.num_records = qs.count()
        return qs


class HomeView(RecordListView):
    page_class = 'collection'


class GenreView(RecordListView):

    def dispatch(self, *a, **k):
        self.genre = Genre.objects.get(pk=self.kwargs['pk'])
        self.page_subtitle = 'Genre: {}'.format(self.genre.name)
        return super().dispatch(*a, **k)

    def get_queryset(self):
        qs = Record.objects.filter(
            genres=self.genre
        ).distinct().order_by(self.get_sort())
        self.num_records = qs.count()
        return qs


class StyleView(RecordListView):
    """
    Displays our standard record list view limited to one particular
    style (basically a Discogs tag).
    """

    def dispatch(self, *a, **k):
        self.style = Style.objects.get(pk=self.kwargs['pk'])
        self.page_subtitle = 'Style: {}'.format(self.style.name)
        return super().dispatch(*a, **k)

    def get_queryset(self):
        qs = Record.objects.filter(
            styles=self.style
        ).distinct().order_by(self.get_sort())
        self.num_records = qs.count()
        return qs


class LabelView(RecordListView):

    def dispatch(self, *a, **k):
        self.label = Label.objects.get(pk=self.kwargs['pk'])
        self.page_subtitle = 'Label: {}'.format(self.label.name)
        return super().dispatch(*a, **k)

    def get_queryset(self):
        qs = Record.objects.filter(
            label=self.label
        ).distinct().order_by(self.get_sort())
        self.num_records = qs.count()
        return qs


class SearchView(RecordListView):

    def get_queryset(self):
        query = self.request.GET['query']
        qs = self.model.objects.filter(
            Q(title__icontains=query) | Q(artist__name__icontains=query)
        ).order_by(self.get_sort()).distinct()
        self.num_records = qs.count()
        return qs


class RecordView(DetailView):
    model = Record

    def scrobbles_by_year(self):
        record = self.get_object()
        scrobbles = record.scrobble_set.all()
        return lastfm.scrobbles_by_year_for_queryset(scrobbles)

    def get_scrobble_form(self):
        today = timezone.make_aware(
            datetime.datetime.now()
        ).strftime('%Y %m %d')
        now   = timezone.make_aware(datetime.datetime.now()).strftime('%H:%M')
        form  = forms.ScrobbleForm(
            initial=dict(
                date=today, time=now, record_id=self.get_object().id
            )
        )
        return form


class SubmitScrobbleView(FormView):
    form_class  = forms.ScrobbleForm
    success_url = reverse_lazy('scrobble-list')

    def form_valid(self, form):
        data = form.cleaned_data
        year, month, day = [int(i) for i in data['date'].split(' ')]
        hour, minute = [int(i) for i in data['time'].split(':')]
        date = datetime.datetime(year, month, day, hour, minute)

        record = Record.objects.get(pk=data['record_id'])

        lastfm.scrobble_record(record, date)

        lastfm.load_last_24_hours_of_scrobbles()
        return super().form_valid(form)


class DeleteRecordView(DeleteView):
    model = Record
    success_url = reverse_lazy('home')


class ArtistView(DetailView):
    model = Artist

    def scrobbles_by_year(self):
        artist = self.get_object()
        scrobbles = artist.scrobble_set.all()
        return lastfm.scrobbles_by_year_for_queryset(scrobbles)


class ScrobbleListView(ListView):
    model = Scrobble
    paginate_by = 50
    page_class = 'scrobbles'

    def get_queryset(self):
        return Scrobble.objects.all().order_by('-timestamp')

    def num_scrobbles(self):
        return Scrobble.objects.count()

    def get_scrobbles_by_year(self):
        return lastfm.total_scrobbles_by_year()

class UnlinkedScrobbleView(ListView):
    template_name = 'inasilentway/unlinked_scrobbles.html'
    model = Scrobble
    paginate_by = 50

    def total_scrobbles(self):
        return Scrobble.objects.count()

    def get_queryset(self):
        qs = Scrobble.objects.filter(
            isw_album__isnull=True,
            album__isnull=False
        )
        self.num_scrobbles = qs.count()
        return qs


class RecentlyScrobbledRecordsView(TemplateView):
    template_name = 'inasilentway/recently_scrobbled_record_list.html'

    def get_recent_scrobbles(self):
        seen    = set()
        recents = []
        recently_scrobbled = Scrobble.objects.filter(
            isw_album__isnull=False
        ).order_by('-timestamp')

        for scrobble in recently_scrobbled:

            play = (
                scrobble.isw_album.title,
                scrobble.datetime.strftime('%d %m %y')
            )

            if play not in seen:
                recents.append(scrobble.isw_album)
                seen.add(play)

            if len(recents) == 30:
                print(seen)
                return recents


class ListeningHistoryView(TemplateView):
    """
    Presents an overview of listening history, with methods to calculate
    various numbers, lists and charts.
    """
    template_name = 'inasilentway/listening_history.html'

    # Top artist lists
    def get_top_artists(self):
        return Artist.objects.all().annotate(
            total=Count('scrobble')).order_by('-total')[:20]

    def get_top_lastfm_artists_all_time(self):
        return Scrobble.objects.all().values(
            'artist').annotate(total=Count('artist')).order_by('-total')[:20]

    def get_top_lastfm_artists_this_year(self):
        today = datetime.date.today()
        start = time.mktime(datetime.datetime(today.year, 1, 1, 0, 0).timetuple())
        return Scrobble.objects.filter(timestamp__gte=start).values(
            'artist').annotate(total=Count('artist')).order_by('-total')[:20]

    def get_top_lastfm_artists_this_month(self):
        today = datetime.date.today()
        start = time.mktime(datetime.datetime(today.year, today.month, 1, 0, 0).timetuple())
        return Scrobble.objects.filter(timestamp__gte=start).values(
            'artist').annotate(total=Count('artist')).order_by('-total')[:20]

    # Count / Avg pairs

    def _scrobbles_per_day_between(self, start, end):
        """
        Given two datetime.dates return the average number of
        scrobbles per day between them
        """
        days = (end - start).days
        qs   = Scrobble.objects.filter(
            timestamp__gte=time.mktime(start.timetuple()),
            timestamp__lt=time.mktime(end.timetuple())
        )
        count = qs.count()

        return {
            'per_day': int(float(count) / days),
            'count'  : count
        }

    def get_scrobbles_per_day_all_time(self):
        qs    = Scrobble.objects.all().order_by('timestamp')
        start = qs.first().ts_as_dt()
        end   = qs.last().ts_as_dt()
        return self._scrobbles_per_day_between(start, end)

    def get_scrobbles_per_day_this_year(self):
        today = datetime.date.today()
        start = datetime.datetime(today.year, 1, 1)
        end   = datetime.datetime.combine(
            today, datetime.datetime.min.time()
        ) + datetime.timedelta(days=1)
        return self._scrobbles_per_day_between(start, end)

    def get_scrobbles_per_day_this_month(self):
        today = datetime.date.today()
        year  = today.year
        month = today.month
        start = datetime.datetime(year, month, 1)
        end   = datetime.datetime(year, month, today.day +1)
        return self._scrobbles_per_day_between(start, end)

    # Graphs

    def get_scrobble_graph_this_month(self):
        now = datetime.datetime.now()
        start = datetime.datetime(now.year, now.month, 1)
        queryset = Scrobble.objects.filter(
            timestamp__gte=time.mktime(start.timetuple()),
            timestamp__lt=time.mktime(now.timetuple())
        )
        return lastfm.scrobbles_by_day_for_queryset(queryset)

    def get_scrobble_graph_this_year(self):
        now = datetime.datetime.now()
        start = datetime.datetime(now.year, 1, 1)
        qs = Scrobble.objects.filter(
            timestamp__gte=time.mktime(start.timetuple()),
            timestamp__lt=time.mktime(now.timetuple())
        )
        return lastfm.scrobbles_by_month_for_queryset(qs)

    def get_scrobble_graph_all_time(self):
        return lastfm.total_scrobbles_by_year()
