"""
Views for inasilentway
"""
import collections
import datetime
import random
import time

from django.db.models import Count, Q, Max
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.functional import cached_property
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

    def sort(self, queryset):
        sorts = {
            'artist': 'artist__name',
            'title ': 'title',
            'year'  : 'year',
            'oldest': 'oldest'
        }

        if self.request.GET.get('sort', None) in sorts:
            sort = sorts[self.request.GET['sort']]
        else:
            sort = 'title'
        if sort == 'oldest':
            queryset = queryset.filter(scrobble__isnull=False)
            queryset = queryset.annotate(last_scrobble=Max('scrobble__timestamp'))
            queryset = queryset.order_by('last_scrobble').distinct()
        else:
            queryset = queryset.order_by(sort).distinct()
        return queryset

    def get_queryset(self):
        qs = self.model.objects.filter(
            title__isnull=False
        )
        qs = self.sort(qs)
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
        )
        qs = self.sort(qs)
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
        )
        qs = self.sort(qs)
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
        )
        qs = self.sort(qs)
        self.num_records = qs.count()
        return qs


class UnplayedView(RecordListView):
    """
    Displays our standard record list view limited to records
    that do not yet have a linked scrobble.
    """
    page_title    = 'Unplayed Records'
    page_subtitle = 'Unplayed Records'

    def get_queryset(self):
        qs = self.model.objects.filter(
            scrobble__isnull=True
        )
        qs = qs.exclude(artist__name='Various')
        qs = self.sort(qs)
        self.num_records = qs.count()
        return qs


class OldestView(RecordListView):

    page_subtitle = 'Least recently played records'

    def get_queryset(self):
        qs = self.model.objects.filter(
            scrobble__isnull=False
        )
        qs = qs.annotate(last_scrobble=Max('scrobble__timestamp'))
        qs = qs.order_by('last_scrobble')
        self.num_records = qs.count()
        return qs


class SearchView(RecordListView):

    def get_song_queryset(self, query):
        operator, title = query.split(':')
        return self.sort(self.model.objects.filter(
            track__title__icontains=title
        ))

    def get_queryset(self):
        query = self.request.GET['query']
        if query.startswith('song:'):
            qs = self.get_song_queryset(query)
        else:
            qs = self.model.objects.filter(
                Q(title__icontains=query) | Q(artist__name__icontains=query)
            )
            qs = self.sort(qs)

        self.num_records = qs.count()
        return qs


class RecordView(DetailView):
    model = Record

    def page_title(self):
        record = self.get_object()
        return record.title

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
                date=today, time=now, record_id=self.get_object().id,
                tracks='*'
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

        if data['tracks'] == '*':
            print('Scrobbling all tracks')
            lastfm.scrobble_record(record, date)
        else:
            print('Scrobbling track subset from record')
            tracks = lastfm.filter_tracks(record, data['tracks'])
            lastfm.scrobble_tracks(tracks, date)

        try:
            lastfm.load_last_24_hours_of_scrobbles()
        except lastfm.pylast.WSError:
            return redirect(reverse('scrobble-retrieval-error'))
        return super().form_valid(form)


class ScrobbleRetrievalErroView(TemplateView):
    template_name = 'inasilentway/scrobble_retrieval_error.html'


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
    page_title = 'Scrobbles'

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
            isw_track__isnull=True,
            title__isnull=False
        ).order_by('-timestamp')
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
    page_title = 'Listening history'

    # Top artist lists
    def _top_scrobbles_for_qs(self, qs):
        return qs.values(
            'artist').annotate(total=Count('artist')).order_by('-total')[:25]

    @cached_property
    def get_top_lastfm_artists_all_time(self):
        return self._top_scrobbles_for_qs(Scrobble.objects.all())

    def get_top_lastfm_artists_this_year(self):
        today   = datetime.date.today()
        start   = time.mktime(datetime.datetime(today.year, 1, 1, 0, 0).timetuple())
        scrobbles = self._top_scrobbles_for_qs(
            Scrobble.objects.filter(timestamp__gte=start)
        )

        all_time_rankings = {}
        for i, s in enumerate(self.get_top_lastfm_artists_all_time):
            all_time_rankings[s['artist']] = i+1

        for i, scrobble in enumerate(scrobbles):
            ranking = dict(icon='&nwArr;', klass='gold')

            i += 1
            if scrobble['artist'] in all_time_rankings:
                all_time = all_time_rankings[scrobble['artist']]
                if all_time == i:
                    ranking = dict(icon='&mapstoleft;', klass='navy')
                elif all_time > i:
                    ranking = dict(icon='&uparrow;', klass='dark-green')
                elif all_time < i:
                    ranking = dict(icon='&downarrow;', klass='dark-red')

            scrobble['all_time_ranking'] = ranking

        return scrobbles

    def get_top_lastfm_artists_this_month(self):
        today = datetime.date.today()
        start = time.mktime(datetime.datetime(today.year, today.month, 1, 0, 0).timetuple())
        return Scrobble.objects.filter(timestamp__gte=start).values(
            'artist').annotate(total=Count('artist')).order_by('-total')[:25]

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
        try:
            end   = datetime.datetime(year, month, today.day +1)
        except ValueError:
            end = datetime.datetime(year, month, today.day)
            end = end + datetime.timedelta(days=1)

        return self._scrobbles_per_day_between(start, end)

    # Graphs

    def get_scrobble_graph_this_month(self):
        now = datetime.datetime.now()
        start = datetime.datetime(now.year, now.month, 1)
        queryset = Scrobble.objects.filter(
            timestamp__gte=time.mktime(start.timetuple()),
            timestamp__lt=time.mktime(now.timetuple())
        )
        return lastfm.scrobbles_by_day_for_queryset(queryset, min_values=12)

    def get_scrobble_graph_this_year(self):
        now = datetime.datetime.now()
        start = datetime.datetime(now.year, 1, 1)
        qs = Scrobble.objects.filter(
            timestamp__gte=time.mktime(start.timetuple()),
            timestamp__lt=time.mktime(now.timetuple())
        )
        data = lastfm.scrobbles_by_month_for_queryset(qs)
        months = {
            1: 'Jan',
            2: 'Feb',
            3: 'Mar',
            4: 'Apr',
            5: 'May',
            6: 'Jun',
            7: 'Jul',
            8: 'Aug',
            9: 'Sep',
            10: 'Oct',
            11: 'Nov',
            12: 'Dec'
        }
        year = str(start.year)
        data = [
            ({'y': months[y], 'link': reverse('listening-history-month', args=[year, months[y]]) },
             value, proportion)
            for y, value, proportion in data
        ]
        return data

    def get_scrobble_graph_all_time(self):
        data = lastfm.total_scrobbles_by_year()
        data = [
            ({'y': y, 'link': reverse('listening-history-year', args=[y]) }, value, proportion)
            for y, value, proportion in data
        ]
        return data


class ListeningHistoryYearView(ListeningHistoryView):
    template_name = 'inasilentway/listening_history_year.html'

    def dispatch(self, *a, **k):
        self.year  = k.get('year', None)
        self.start = datetime.datetime(self.year, 1, 1)
        self.end   = datetime.datetime(self.year + 1, 1, 1)
        self.lastfm_subheading = 'Last.fm &mdash; {}'.format(self.year)

        return super().dispatch(*a, **k)

    def get_scrobbles_per_day_this_year(self):
        return self._scrobbles_per_day_between(self.start, self.end)

    def get_scrobble_graph_this_year(self):
        qs = Scrobble.objects.filter(
            timestamp__gte=time.mktime(self.start.timetuple()),
            timestamp__lt=time.mktime(self.end.timetuple())
        )
        return lastfm.scrobbles_by_month_for_queryset(qs)

    def get_top_lastfm_artists_this_year(self):
        scrobbles = self._top_scrobbles_for_qs(
            Scrobble.objects.filter(
                timestamp__gte=time.mktime(self.start.timetuple()),
                timestamp__lt=time.mktime(self.end.timetuple())
            )
        )

        prev_year_rankings = {}
        prev_year_top = self._top_scrobbles_for_qs(
            Scrobble.objects.filter(
                timestamp__gte=time.mktime(
                    datetime.datetime(self.year -1, 1, 1).timetuple()),
                timestamp__lt=time.mktime(
                    self.start.timetuple())
            )
        )
        for i, s in enumerate(prev_year_top):
            prev_year_rankings[s['artist']] = i+1

        for i, scrobble in enumerate(scrobbles):
            ranking = dict(icon='&nwArr;', klass='gold')

            i += 1
            if scrobble['artist'] in prev_year_rankings:
                all_time = prev_year_rankings[scrobble['artist']]
                if all_time == i:
                    ranking = dict(icon='&mapstoleft;', klass='navy')
                elif all_time > i:
                    ranking = dict(icon='&uparrow;', klass='dark-green')
                elif all_time < i:
                    ranking = dict(icon='&downarrow;', klass='dark-red')

            scrobble['all_time_ranking'] = ranking

        return scrobbles


class ListeningHistoryMonthView(ListeningHistoryView):
    template_name = 'inasilentway/listening_history_month.html'

    def dispatch(self, *a, **k):
        months = {
            'Jan': 1,
            'Feb': 2,
            'Mar': 3,
            'Apr': 4,
            'May': 5,
            'Jun': 6,
            'Jul': 7,
            'Aug': 8,
            'Sep': 9,
            'Oct': 10,
            'Nov': 11,
            'Dec': 12
        }

        self.year  = k.get('year', None)
        self.month = k.get('month', None)
        self.start = datetime.datetime(self.year, months[self.month], 1)
        self.end   = datetime.datetime(self.year, months[self.month] + 1, 1)
        self.lastfm_subheading = 'Last.fm &mdash; {} {}'.format(self.month, self.year)

        return super().dispatch(*a, **k)

    def get_scrobbles_per_day_this_month(self):
#        today = datetime.date.today()
#        year  = today.year
#        month = today.month
#        start = datetime.datetime(year, month, 1)
        # try:
        #     end   = datetime.datetime(year, month, today.day +1)
        # except ValueError:
        #     end = datetime.datetime(year, month, today.day)
        #     end = end + datetime.timedelta(days=1)

        return self._scrobbles_per_day_between(self.start, self.end)


    def get_scrobble_graph_this_month(self):
#        now = datetime.datetime.now()
#        start = datetime.datetime(now.year, now.month, 1)
        queryset = Scrobble.objects.filter(
            timestamp__gte=time.mktime(self.start.timetuple()),
            timestamp__lt=time.mktime(self.end.timetuple())
        )
        return lastfm.scrobbles_by_day_for_queryset(queryset, min_values=12)


class TopArtistsView(ListView):

    template_name = 'inasilentway/top_artists.html'
    model = Scrobble
    paginate_by = 50

    def get_ol_start(self):
        return ((self.get_context_data()['page_obj'].number - 1 )* self.paginate_by ) + 1

    def get_queryset(self):
        return Scrobble.objects.all().values('artist').annotate(
            total=Count('artist')).order_by('-total')
