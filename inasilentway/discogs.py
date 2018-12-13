"""
Interacting with Discogs from Inasilentway
"""
import time

from dateutil import parser
import discogs_client
from django.conf import settings
from django.db import transaction

from inasilentway import models


api = discogs_client.Client(
    'Inasilentway',
    user_token=settings.DISCOGS_USER_TOKEN
)

def save_artist_from_discogs_data(artist_data):
    """
    Given a discogs artist instance, save it to our database
    if it doesn't exist
    """
    art, _ = models.Artist.objects.get_or_create(discogs_id=artist_data.id)

    art.name    = artist_data.name
    try:
        art.images  = artist_data.images
    except discogs_client.exceptions.HTTPError:
        pass  # 404 on the artist images happens sometimes apparently?
    try:
        art.url     = artist_data.url
    except discogs_client.exceptions.HTTPError:
        pass  # 404 on the artist images happens sometimes apparently?
    try:
        art.profile = artist_data.profile
    except discogs_client.exceptions.HTTPError:
        pass  # 404 on the artist images happens sometimes apparently?
    try:
        art.urls    = artist_data.urls
    except discogs_client.exceptions.HTTPError:
        pass  # 404 on the artist images happens sometimes apparently?

    art.save()
    return art


def save_label_from_discogs_data(label_data):
    """
    Given a discogs label instance, save it to our database if it doesn't exist
    """
    label, _ = models.Label.objects.get_or_create(
        discogs_id=label_data.id)
    label.name = label_data.name
    label.save()
    return label


def save_record_from_discogs_data(record):
    """
    Given a Discogs record instance, save it to our database
    """
    artists = [
        save_artist_from_discogs_data(a) for a in record.release.artists
    ]

    rec, _ = models.Record.objects.get_or_create(discogs_id=record.release.id)

    for artist in artists:
        rec.artist.add(artist)

    for genre in record.release.genres:
        g, _ = models.Genre.objects.get_or_create(name=genre)
        rec.genres.add(g)

    if record.release.styles:
        for style in record.release.styles:
            s, _ = models.Style.objects.get_or_create(name=style)
            rec.styles.add(s)

    rec.thumb = record.release.thumb

    rec.label   = save_label_from_discogs_data(record.release.labels[0])
    rec.title   = record.release.title
    rec.year    = record.release.year
    rec.images  = record.release.images
    rec.country = record.release.country
    rec.notes   = record.release.notes
    rec.formats = '{}, {}'.format(
        record.release.formats[0]['name'],
        ' '.join(record.release.formats[0]['descriptions'])
    )
    rec.url     = record.release.url
    rec.status  = record.release.status
    rec.date_added = parser.parse(record.data['date_added'])
    rec.save()

    # Tracks don't have an ID so kill them all
    models.Track.objects.filter(record=rec).delete()
    for track in record.release.tracklist:
        models.Track(
            record=rec,
            duration=track.duration,
            position=track.position,
            title=track.title
        ).save()

    return rec


def load_record(record_data):
    """
    Given a Discogs API object representing a single record, load
    that record into our database.
    """
    try:
        with transaction.atomic():
            return save_record_from_discogs_data(record_data)

    except discogs_client.exceptions.HTTPError:
        print('Discogs API rate limit exceeded, sleeping for 61s')
        time.sleep(61)
        return load_record(record_data)


def load_collection():
    """
    Load the users entire collection
    into our local copy
    """
    user = api.user(settings.DISCOGS_USER)
    records = user.collection_folders[0].releases
    print('{} records in collection'.format(user.num_collection))
    for record in records:
        if models.Record.objects.filter(discogs_id=record.release.id).exists():
            print('Skipping {} - already loaded'.format(record.release.title))
            continue

        instance = load_record(record)
        print('Added {}'.format(instance))
