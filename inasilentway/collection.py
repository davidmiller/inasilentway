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
        return pickle.loads(CACHE_PATH.contents)
    else:
        print "No local record cache larry :("
        sys.exit(1)

def download(args):
    records = get_collection()
    api = discogs.Client('A test application')
    me = api.user('thatdavidmiller')
    if len(records) != me.num_collection:
        print 'fetching data...'
        records = [r for r in me.collection_folders[0].releases]
        print 'fetched record data'
        CACHE_PATH << pickle.dumps(records)
        print 'written record data to local cache'

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
    print 'Collection available as `records`'
    import pdb;pdb.set_trace()
