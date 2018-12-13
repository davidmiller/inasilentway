"""
Unittests for inasilentway.models
"""
from django.test import TestCase

from inasilentway import models


class ArtistTestCase(TestCase):

    def test_get_absolute_url(self):
        artist = models.Artist.objects.create()
        self.assertEqual('/artist/1/', artist.get_absolute_url())
