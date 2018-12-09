import pickle


import ffs


HERE = ffs.Path.here()
CACHE_PATH = HERE/'data/collection.pickle'

records = []

if CACHE_PATH:
    records = pickle.loads(CACHE_PATH.contents)

api = discogs.Client('A test application')
me = api.user('thatdavidmiller')

print me
print me.num_collection, 'in collection', len(records), 'in cache'

#import pdb;pdb.set_trace()

if len(records) != me.num_collection:
    print 'fetching data...'

    records = [r for r in me.collection_folders[0].releases]
    CACHE_PATH << pickle.dumps(records)
