"""
Interacting with Discogs from Inasilentway
"""
import json
import time

from dateutil import parser
import discogs_client
from django.conf import settings
from django.db import transaction
import requests

from inasilentway import models

try:
    api = discogs_client.Client(
        'Inasilentway/2.0',
        user_token=settings.DISCOGS_USER_TOKEN
    )

except AttributeError:
    print('No Discogs user token found')
    api = None

def save_artist_from_discogs_data(artist_data):
    """
    Given a discogs artist instance, save it to our database
    if it doesn't exist
    """
    art, _ = models.Artist.objects.get_or_create(discogs_id=artist_data.id)

    art.name    = artist_data.name
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

    try:
        if not isinstance(artist_data.images, list):
            if artist_data.images is None:
                images = []
            else:
                images  = json.loads(artist_data.images)
        else:
            images = artist_data.images

        art.artistimage_set.all().delete()
        for image in images:
            del image['uri150']
            image['artist'] = art
            image['category'] = image['type']
            del image['type']
            image = models.ArtistImage.objects.create(**image)
            image.save()

    except discogs_client.exceptions.HTTPError:
        pass  # 404 on the artist images happens sometimes apparently?

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


def save_record_from_discogs_data(record, added=None):
    """
    Given a Discogs record instance, save it to our database
    """
    artists = [
        save_artist_from_discogs_data(a) for a in record.artists
    ]

    rec, created = models.Record.objects.get_or_create(discogs_id=record.id)

    for artist in artists:
        rec.artist.add(artist)

    for genre in record.genres:
        g, _ = models.Genre.objects.get_or_create(name=genre)
        rec.genres.add(g)

    if record.styles:
        for style in record.styles:
            s, _ = models.Style.objects.get_or_create(name=style)
            rec.styles.add(s)

    rec.label   = save_label_from_discogs_data(record.labels[0])
    rec.title   = record.title
    rec.year    = record.year
    rec.images  = record.images
    rec.country = record.country
    rec.notes   = record.notes
    rec.formats = '{}, {}'.format(
        record.formats[0]['name'],
        ' '.join(record.formats[0]['descriptions'])
    )
    rec.url        = record.url
    rec.status     = record.status

    if added:
        rec.date_added = added

    rec.save()

    # Artwork requires secret/key urls not supported by this client so
    # fetch them ourselves
    save_thumb(rec)

    # Tracks don't have an ID so kill them all
    models.Track.objects.filter(record=rec).delete()
    for track in record.tracklist:
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
            return save_record_from_discogs_data(record_data.release)

    except discogs_client.exceptions.HTTPError:
        print('Discogs API rate limit exceeded, sleeping for 61s')
        time.sleep(61)
        # Unsure what this was here for, but it raises, so removing
        # return load_record(record_data.release, added=parser.parse(record.data['date_added']))
        return load_record(record_data)
    except requests.exceptions.ConnectionError:
        print('"Connection error", sleeping for 61s')
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
            if record.release.id != '21029362':
                print('Skipping {} - already loaded'.format(record.release.title))
                continue

        instance = load_record(record)
        print('Added {}'.format(instance))


def save_thumb(record):
    """
    Given a Record instance, get it's thumb from upstream
    """
    data = api.release(record.discogs_id)
    url = f"https://api.discogs.com/releases/{record.discogs_id}?key={settings.DISCOGS_KEY}&secret={settings.DISCOGS_SECRET}"
    response = requests.get(url)
    data = response.json()
    thumb_url = data['thumb']
    record.thumb = thumb_url
    record.save()
