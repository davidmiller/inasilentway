# """
# interact with Last.fm
# """
# import datetime
# import time

# import pylast

# from inasilentway import utils

# LASTFM_CORRECTIONS = {
#     # Sometimes Last.fm "corrects" album titles.
#     # Where these are different to Discogs album title versions this means we
#     # are unable to match the scrobbles to the album.
#     #
#     # We keep a mapping of known corrections here so we can move between them
#     #
#     'album': {
#         'Desafinado: Bossa Nova & Jazz Samba': 'Desafinado Coleman Hawkins Plays Bossa Nova & Jazz Samba', # noqa
#         'Oscar Peterson Plays the Duke Ellington Songbook': 'The Duke Ellington Songbook', # noqa
#         'Standard Time Vol.2 - Intimacy Calling': 'Standard Time Vol. 2 (Intimacy Calling)', # noqa
#         'White Light/White Heat': 'White Light / White Heat',
#     },

#     'artist': {
#         'Duke Ellington & His Orchestra': 'Duke Ellington And His Orchestra'
#     }
# }

# SPOTIFY_EQUIVALENTS = {
#     'album': {
#         'Way Out West (OJC Remaster)': 'Way Out West',
#         "Workin' (RVG Remaster)": "Workin' With The Miles Davis Quintet"
#     }
# }


# def get_lastfm():
#     utils.setup_django()
#     from django.conf import settings

#     lastfm = pylast.LastFMNetwork(
#         api_key=settings.LASTFM_API_KEY,
#         api_secret=settings.LASTFM_SECRET,
#         username=settings.LASTFM_USER,
#         password_hash=settings.LASTFM_PASS
#     )
#     return lastfm


# def scrobble_django_record(record, when):
#     # TODO: Rename this

#     start_time = time.mktime(when.timetuple())
#     tracks = []
#     for track in record.track_set.all():
#         tracks.append(
#             {
#                 'artist'   : record.artist.first().name,
#                 'title'    : track.title,
#                 'album'    : record.title,
#                 'timestamp': start_time
#             }
#         )
#         if track.duration:
#             mins, secs = track.duration.split(':')
#             seconds = int(secs) + (int(mins) * 60)
#             start_time += seconds
#         else:
#             start_time += (3 * 60) + 41

#     lastfm = get_lastfm()
#     lastfm.scrobble_many(tracks)


# def get_scrobbles():
#     """
#     Get this user's scrobbles. All of them.
#     """
#     from django.conf import settings

#     from inasilentway.models import Scrobble

#     lastfm = get_lastfm()

#     if Scrobble.objects.count() > 0:
#         # oldest = Scrobble.objects.all().order_by('timestamp').first()
#         # oldest_scrobble = oldest.timestamp
#         newest = Scrobble.objects.all().order_by('timestamp').last()
#         print(newest.title)
#         newest_scrobble = newest.timestamp

#     user = lastfm.get_user(settings.LASTFM_USER)
#     tracks = user.get_recent_tracks(limit=1000, time_from=newest_scrobble)
#     print(tracks)
#     return tracks


# def save_scrobbles(scrobbles):
#     """
#     Give some scrobbles, save them to the database
#     """
#     from inasilentway.models import Scrobble
#     from django.utils import timezone

#     for scrobble in scrobbles:
#         scrob, _ = Scrobble.objects.get_or_create(
#             timestamp=scrobble.timestamp,
#             title=scrobble.track.title
#         )
#         scrob.artist = scrobble.track.artist
#         scrob.album  = scrobble.album
#         scrob.timestamp = int(scrobble.timestamp)
#         format_string = '%d %b %Y, %H:%M'
#         scrob.datetime = timezone.make_aware(
#             datetime.datetime.strptime(scrobble.playback_date, format_string)
#         )
#         scrob.save()


# def save_scrobbles_since(when):
#     from django.conf import settings

#     lastfm = get_lastfm()
#     user = lastfm.get_user(settings.LASTFM_USER)

#     tracks = user.get_recent_tracks(
#         limit=1000, time_from=time.mktime(when.timetuple()))
#     save_scrobbles(tracks)


# def load_scrobbles(args):
#     """
#     Commandline entrypoint to get scrobbles and print them (warning, big)
#     """
#     utils.setup_django()
#     scrobbles = get_scrobbles()
#     save_scrobbles(scrobbles)
#     from inasilentway.models import Scrobble
#     print('We have {} scrobbles'.format(Scrobble.objects.count()))
#     if len(scrobbles) > 0:
#         print('Going again')
#         load_scrobbles(args)


# def match_artist(artist_name):
#     """
#     Given the name of an artist, return a matching Artist
#     or None
#     """
#     from inasilentway.models import Artist

#     artist_matches = Artist.objects.filter(
#         name__iexact=artist_name
#     )

#     if len(artist_matches) == 0:
#         if artist_name in LASTFM_CORRECTIONS['artist']:
#             return match_artist(LASTFM_CORRECTIONS['artist'][artist_name])
#         return None

#     if len(artist_matches) == 1:
#         return artist_matches[0]

#     if len(artist_matches) > 1:
#         import pdb; pdb.set_trace() # noqa
#         print(artist_matches)


# def match(artist, album, title):
#     """
#     Return matches if we have them or none
#     """
#     from inasilentway.models import Record

#     match_album = None
#     match_track = None

#     matching_artist = match_artist(artist)

#     if album in LASTFM_CORRECTIONS['album']:
#         album = LASTFM_CORRECTIONS['album'][album]

#     album_matches = Record.objects.filter(
#         title__iexact=album,
#         artist=matching_artist
#     )

#     if len(album_matches) == 0:
#         return matching_artist, match_album, match_track

#     if len(album_matches) == 1:
#         match_album = album_matches[0]

#     if len(album_matches) > 1:
#         # E.g. Billie holiday with many "all or nothing at all" albums
#         return matching_artist, match_album, match_track

#     for track in match_album.track_set.all():
#         if track.title.lower() == title.lower():
#             match_track = track

#     return matching_artist, match_album, match_track


# def make_links(scrobbles):

#     print('{} unlinked scrobbles'.format(scrobbles.count()))
#     matches_added = 0

#     for scrobble in scrobbles:
#         matches = match(scrobble.artist, scrobble.album, scrobble.title)
#         artist, album, track = matches

#         if track:
#             scrobble.isw_track = track

#         if artist:
#             scrobble.isw_album = album
#             matches_added += 1

#         if album:
#             scrobble.isw_artist = artist

#         if any([track, artist, album]):
#             scrobble.save()

#         else:
#             print('No matches, next')
#             continue

#     print('This run added {} album matches'.format(matches_added))


# def link_scrobbles(args):
#     """
#     Commandline entrypoint to get scrobbles and link them with
#     records in our collection
#     """
#     utils.setup_django()

#     from inasilentway.models import Scrobble

#     unlinked = Scrobble.objects.filter(
#         isw_album__isnull=True,
#         album__isnull=False
#     )
#     make_links(unlinked)
