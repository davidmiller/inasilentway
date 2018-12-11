"""
Collection utilities
"""
import os
import pickle
import random
import sys
import time

import ffs
import discogs_client as discogs

from inasilentway import output, utils

HERE = ffs.Path.here()
CACHE_PATH = HERE/'../data/collection.pickle'


def get_collection():
    if CACHE_PATH:
        with open(CACHE_PATH.abspath, 'rb') as fh:
            return pickle.load(fh)
    else:
        print("No local record cache larry :(")


def choose_record(records, genre=None, **kwargs):
    record = random.choice(records)
    if genre:
        while genre.lower() not in [g.lower() for g in record.release.genres]:
            record = random.choice(records)
    return record


def _match(record, term):
    """
    Predicate function to determine whether RECORD matches
    TERM
    """
    term = term.lower()

    if term in record.release.title.lower():
        return True

    for artist in record.release.artists:
        if term in artist.name.lower():
            return True

    return False


def search(term):
    """
    Search the collection for TERM return matches.
    """
    collection = get_collection()
    matches = [r for r in collection if _match(r, term)]
    return sorted(matches, key=lambda x: x.release.title)


def save_record_from_discogs_data(record):
    """
    Given a Discogs record instance, save it to our database
    """
    from inasilentway import models

    artists = []
    for artist in record.release.artists:
        art, _ = models.Artist.objects.get_or_create(discogs_id=artist.id)

        art.name    = artist.name
        try:
            art.images  = artist.images
            art.url     = artist.url
            art.profile = artist.profile
            art.urls    = artist.urls
        except discogs.exceptions.HTTPError:
            pass # 404 on the artist images happens sometimes apparently?
        art.save()

        artists.append(art)

    label, _ = models.Label.objects.get_or_create(discogs_id=record.release.labels[0].id)
    label.name = record.release.labels[0].name
    label.save()

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

    api = discogs.Client('inasilentway', user_token='PYffmSZeeqHUYaMWMEjwGhqfSWtOBFcPOggoixmD')
    api_release = api.release(rec.discogs_id)
    rec.thumb = api_release.thumb

    rec.label   = label
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

"""
Commandline entrypoints from ./shhh (python -m inasilentway )
"""

def download(args):
    """
    Commandline entrypoint to download the collection if we
    have less records in it than in our local cache

    TODO: Convert to Django?
    """
    records = get_collection()

    if records is None:
        records = []
    api = discogs.Client('Inasilentway')
    me = api.user('thatdavidmiller')

    if len(records) != me.num_collection:

        print('fetching data...')

        records = [r for r in me.collection_folders[0].releases]
        print('fetched record data')
        print('{} records'.format(len(records)))

        with open(CACHE_PATH.abspath, 'wb') as fh:
            pickled = pickle.dump(records, fh)

        print('written record data to local cache')


def random_record(args):
    """
    Commandline Entrypoint, select a random record and print
    it to the commandline
    """
    kwargs = {}
    if args.genre:
        kwargs['genre'] = args.genre
    record = choose_record(get_collection(), **kwargs)
    output.print_record(record)
    if args.vinylscrobbler:
        output.open_vnylscrobbler(record)
    return


def collection_shell(args):
    """
    Commandline entrypoint: Drop the user into a pdb shell
    with the collection available as JSON

    TODO: kill this once we have a Django shell?
    """
    records = get_collection()
    print('Collection available as `records`')
    import pdb;pdb.set_trace()


def load_django(args):
    """
    Commandline entrypoint to load our collection into Django
    """
    utils.setup_django()

    download(None)
    collection = get_collection()

    ADDED = 0

    def add_record(record):
        rec = save_record_from_discogs_data(record)
        print('Added {}'.format(rec.title))

    from inasilentway import models

    for record in collection:
        print('Looking at {}'.format(record.release.title))

        # TODO: Undo this when we've figured out how to not freak out
        # the discogs API limits
        if models.Record.objects.filter(discogs_id=record.release.id).exists():
            print('Found {} in local database, skipping'.format(record.release.title))
            continue

        try:
            add_record(record)
            ADDED += 1
            if ADDED == 100:
                break
        except discogs.exceptions.HTTPError:
            print("Got a quick requests warning, sleep for a bit and retry once")
            time.sleep(60)
            add_record(record)

            ADDED += 1
            if ADDED == 100:
                break


        # Prevent HTTPError: 429: You are making requests too quickly.
        time.sleep(2)

    print('Count: {}'.format(models.Record.objects.count()))
