"""
Collection utilities
"""
import pickle
import random
import sys

import ffs
import discogs_client as discogs

from inasilentway import output

HERE = ffs.Path.here()
CACHE_PATH = HERE/'../data/collection.pickle'


def get_collection():
    if CACHE_PATH:
        with open(CACHE_PATH.abspath, 'rb') as fh:
            return pickle.load(fh)
    else:
        print("No local record cache larry :(")

def download(args):
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

def choose_record(records, genre=None, **kwargs):
    record = random.choice(records)
    if genre:
        while genre.lower() not in [g.lower() for g in record.release.genres]:
            record = random.choice(records)
    return record

def random_record(args):
    kwargs = {}
    if args.genre:
        kwargs['genre'] = args.genre
    record = choose_record(get_collection(), **kwargs)
    output.print_record(record)
    if args.vinylscrobbler:
        output.open_vnylscrobbler(record)
    return

def collection_shell(args):
    records = get_collection()
    print('Collection available as `records`')
    import pdb;pdb.set_trace()

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
