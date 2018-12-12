"""
Models for inasilentway
"""
import datetime

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Genre(models.Model):
    """
    A Genre of music as defined by Discogs
    (Basically a tag)
    """
    name = models.CharField(max_length=200)

    def get_absolute_url(self):
        return reverse('genre', args=[self.id])


class Style(models.Model):
    """
    A style of music as defined by Discogs
    (Basically a tag)
    """
    name = models.CharField(max_length=200)


class Artist(models.Model):
    """
    An Artist
    """
    discogs_id = models.CharField(max_length=200)
    name       = models.CharField(max_length=200)
    images     = models.CharField(max_length=200, blank=True, null=True)
    url        = models.URLField(blank=True, null=True)
    # What are these?
    profile    = models.CharField(max_length=200)
    urls       = models.CharField(max_length=200, blank=True, null=True)

    def get_absolute_url(self):
        return reverse('artist', args=[self.id])


class Label(models.Model):
    """
    A record label
    """
    discogs_id = models.CharField(max_length=200)
    name = models.CharField(max_length=200)

    def get_absolute_url(self):
        return reverse('label', args=[self.id])



class Record(models.Model):
    """
    An individual record
    """
    discogs_id = models.CharField(max_length=200)
    artist  = models.ManyToManyField(Artist)
    genres  = models.ManyToManyField(Genre)
    styles  = models.ManyToManyField(Style)

    label   = models.ForeignKey(Label, on_delete=models.CASCADE, blank=True, null=True)
    title   = models.CharField(max_length=200, blank=True, null=True)
    year    = models.CharField(max_length=200, blank=True, null=True)
    thumb   = models.CharField(max_length=200, blank=True, null=True)
    images  = models.CharField(max_length=200, blank=True, null=True)
    country = models.CharField(max_length=200, blank=True, null=True)
    notes   = models.CharField(max_length=200, blank=True, null=True)
    formats = models.CharField(max_length=200, blank=True, null=True)
    url     = models.CharField(max_length=200, blank=True, null=True)
    # What are these?
    status  = models.CharField(max_length=200, blank=True, null=True)

    def get_absolute_url(self):
        return reverse('record', args=[self.id, slugify(self.title)])

    def most_recent_scrobble(self):
        return self.scrobble_set.order_by('timestamp').last()


class Track(models.Model):
    """
    A track on a record
    """
    record = models.ForeignKey(Record, on_delete=models.CASCADE)
    duration = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    title    = models.CharField(max_length=200)


class Scrobble(models.Model):
    """
    A last.fm scrobble
    """
    artist    = models.CharField(max_length=200)
    title     = models.CharField(max_length=200)
    album     = models.CharField(max_length=200, blank=True, null=True)
    # This is the submitted timestamp
    datetime  = models.DateTimeField(blank=True, null=True)
    # This is the timestamp of the listen
    timestamp = models.IntegerField(blank=True, null=True)

    isw_track = models.ForeignKey(
        Track, blank=True, null=True,
        on_delete=models.DO_NOTHING
    )
    isw_album = models.ForeignKey(
        Record, blank=True, null=True,
        on_delete=models.DO_NOTHING
    )
    isw_artist = models.ForeignKey(
        Artist, blank=True, null=True,
        on_delete=models.DO_NOTHING
    )

    def ts_as_str(self):
        return timezone.make_aware(
            datetime.datetime.fromtimestamp(self.timestamp)
        ).strftime('%d %b %y %H:%M')