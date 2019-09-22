"""
Unittests for views
"""
from django.test import TestCase
from django.test.client import RequestFactory
import mock

from inasilentway import models, views


class RecordListViewTestCase(TestCase):

    def test_get_random_record(self):
        record_1 = models.Record.objects.create(title='Kind of blue')
        record_2 = models.Record.objects.create(title='Milestones')

        view = views.RecordListView()

        mock_request = mock.MagicMock(name='Mock Request')
        mock_request.GET = {}
        view.request = mock_request

        redirect = view.redirect_to_random_record()

        potential_redirects = [
            record_1.get_absolute_url(),
            record_2.get_absolute_url()
        ]

        self.assertIn(redirect.url, potential_redirects)

    def test_dispatch_regular(self):
        view = views.RecordListView()
        mock_request = mock.MagicMock(name='Mock Request')
        mock_request.GET = {}
        view.request = mock_request
        view.kwargs = {}

        rf = RequestFactory()

        resp = view.dispatch(rf.get('/'))

        self.assertEqual(200, resp.status_code)

    def test_dispatch_redirect(self):
        models.Record.objects.create(title='Kind of blue')

        view = views.RecordListView()
        mock_request = mock.MagicMock(name='Mock Request')
        mock_request.GET = {'redirect': 'random'}
        view.request = mock_request

        resp = view.dispatch(mock_request)
        self.assertEqual(302, resp.status_code)

    def test_get_sort_unspecified(self):
        view = views.RecordListView()

        mock_request = mock.MagicMock(name='Mock Request')
        mock_request.GET.get.return_value = None
        view.request = mock_request

        self.assertEqual('title', view.get_sort())

    def test_get_sort_specifies_artist(self):
        view = views.RecordListView()

        mock_request = mock.MagicMock(name='Mock Request')
        mock_request.GET = {'sort': 'artist'}
        view.request = mock_request

        self.assertEqual('artist__name', view.get_sort())


class GenreViewTestCase(TestCase):

    def test_dispatch(self):
        genre = models.Genre.objects.create(name='Jazz')

        rf = RequestFactory()
        req = rf.get('/genre/1/')

        view = views.GenreView()
        view.kwargs = {'pk': 1}
        view.request = req

        resp = view.dispatch(req)

        self.assertEqual(200, resp.status_code)
        self.assertEqual('Genre: Jazz', view.page_subtitle)


class LabelViewTestCase(TestCase):

    def test_dispatch(self):
        label = models.Label.objects.create(name='Blue Note')

        rf = RequestFactory()
        req = rf.get('/label/1/')

        view = views.LabelView()
        view.kwargs = {'pk': 1}
        view.request = req

        resp = view.dispatch(req)

        self.assertEqual(200, resp.status_code)
        self.assertEqual('Label: Blue Note', view.page_subtitle)


class ListeningHistoryViewTestCase(TestCase):
    def test_get_top_lastfm_artists_all_time(self):
        scrobble = models.Scrobble.objects.create(
            artist='Cole Porter', title='Love For Sale'
        )
        scrobble = models.Scrobble.objects.create(
            artist='Cole Porter', title='What Is This Thing Called Love'
        )
        artist = models.Artist.objects.create(
            discogs_id=1, name='Cole Porter'
        )

        view = views.ListeningHistoryView()

        expected = [
            {
                'artist': 'Cole Porter',
                'total' : 2,
                'url'   : '/artist/1/cole-porter/'
            }
        ]

        top_artists = view.get_top_lastfm_artists_all_time
        self.assertEqual(expected, list(top_artists))
