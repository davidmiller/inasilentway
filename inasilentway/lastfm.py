"""
Interacting with Last.fm from Inasilentway
"""
import collections
import datetime
import time

from django.conf import settings
from django.utils import timezone
import pylast

from inasilentway.models import Scrobble

LASTFM_PRE_SUBMIT_SUBS = {
    #
    # Sometimes when you give the Last.fm scrobble API the name of something
    # their parser throws it away. So for some selected values we substitue
    # them pre submission (only to re-substitute them once we've gotten the
    # data back).
    #
    # It's an all-round win for 'being clever'.
    #
    'album': {
        "Getz & J.J. 'Live' - Stan Getz & J.J. Johnson": "Getz & J.J. 'Live'"
    },
    'artist': {},
    'title': {}
}


LASTFM_CORRECTIONS = {
    #
    # Sometimes Last.fm "corrects" album titles.
    # Where these are different to Discogs album title versions this means we
    # are unable to match the scrobbles to the album.
    #
    # We keep a mapping of known corrections here so we can move between them
    #
    'album': {
        'Desafinado: Bossa Nova & Jazz Samba': 'Desafinado Coleman Hawkins Plays Bossa Nova & Jazz Samba', # noqa
        'Oscar Peterson Plays the Duke Ellington Songbook': 'The Duke Ellington Songbook', # noqa
        'Standard Time Vol.2 - Intimacy Calling': 'Standard Time Vol. 2 (Intimacy Calling)', # noqa
        'White Light/White Heat': 'White Light / White Heat',
    },

    'artist': {
        'Duke Ellington & His Orchestra': 'Duke Ellington And His Orchestra',
        'Miles Davis Quintet': 'The Miles Davis Quintet',
    }
}

# Put the ones we mangled our side into the corrections dataset without
# needing to re-type them
for substitution_type in LASTFM_PRE_SUBMIT_SUBS:
    for pre, post in LASTFM_PRE_SUBMIT_SUBS[substitution_type].items():
        LASTFM_CORRECTIONS[substitution_type][post] = pre

SPOTIFY_EQUIVALENTS = {
    'album': {
        'Way Out West (OJC Remaster)': 'Way Out West',
        "Workin' (RVG Remaster)": "Workin' With The Miles Davis Quintet"
    }
}


api = pylast.LastFMNetwork(
    api_key=settings.LASTFM_API_KEY,
    api_secret=settings.LASTFM_SECRET,
    username=settings.LASTFM_USER,
    password_hash=settings.LASTFM_PASS
)

def match_artist(artist_name):
    """
    Given the name of an artist, return a matching Artist
    or None
    """
    from inasilentway.models import Artist

    artist_matches = Artist.objects.filter(
        name__iexact=artist_name
    )

    if len(artist_matches) == 0:
        if artist_name in LASTFM_CORRECTIONS['artist']:
            return match_artist(LASTFM_CORRECTIONS['artist'][artist_name])
        return None

    if len(artist_matches) == 1:
        return artist_matches[0]

    if len(artist_matches) > 1:
        import pdb; pdb.set_trace() # noqa
        print(artist_matches)


def match(artist, album, title):
    """
    Return matches if we have them or none
    """
    from inasilentway.models import Record

    match_album = None
    match_track = None

    matching_artist = match_artist(artist)

    if album in LASTFM_CORRECTIONS['album']:
        album = LASTFM_CORRECTIONS['album'][album]

    album_matches = Record.objects.filter(
        title__iexact=album,
        artist=matching_artist
    )

    if len(album_matches) == 0:
        return matching_artist, match_album, match_track

    if len(album_matches) == 1:
        match_album = album_matches[0]

    if len(album_matches) > 1:
        # E.g. Billie holiday with many "all or nothing at all" albums
        return matching_artist, match_album, match_track

    for track in match_album.track_set.all():
        if track.title.lower() == title.lower():
            match_track = track

    return matching_artist, match_album, match_track


def link_scrobble(scrobble):
    """
    Given a scrobble, link it to an artist, track and record
    """
    matches = match(scrobble.artist, scrobble.album, scrobble.title)
    artist, album, track = matches

    if track:
        scrobble.isw_track = track

    if artist:
        scrobble.isw_album = album

    if album:
        scrobble.isw_artist = artist

    scrobble.save()



def save_scrobbles(scrobbles):
    """
    Given some scrobbles, save them to the database
    """
    for scrobble in scrobbles:
        scrob, _ = Scrobble.objects.get_or_create(
            timestamp=scrobble.timestamp,
            title=scrobble.track.title
        )
        scrob.artist = scrobble.track.artist
        scrob.album  = scrobble.album
        scrob.timestamp = int(scrobble.timestamp)
        format_string = '%d %b %Y, %H:%M'
        scrob.datetime = timezone.make_aware(
            datetime.datetime.strptime(scrobble.playback_date, format_string)
        )
        scrob.save()
        link_scrobble(scrob)


def get_scrobble_page(when):
    """
    Get a page of this user's scrobbles.
    """
    user = api.get_user(settings.LASTFM_USER)

    return user.get_recent_tracks(
        limit=1000, time_to=when)


def load_scrobble_history():
    """
    Load the entire history of the users scrobbles.
    """
    if Scrobble.objects.count() == 0:
        # Start a little in the future
        when = datetime.datetime.now() + datetime.timedelta(seconds=300)
        when = time.mktime(when.timetuple())
    else:
        oldest = Scrobble.objects.all().order_by('timestamp').first()
        when   = oldest.timestamp
        when += 300

    scrobbles = get_scrobble_page(when)

    if len(scrobbles) > 0:
        save_scrobbles(scrobbles)
        print('We have {} scrobbles'.format(Scrobble.objects.count()))
        print('Going again')
        load_scrobble_history()


def load_last_24_hours_of_scrobbles():
    """
    (Re-)load the last 24 hours of scrobble history.
    """
    now = timezone.make_aware(datetime.datetime.now())
    yesterday = now - datetime.timedelta(days=1)
    timestamp = time.mktime(yesterday.timetuple())
    user = api.get_user(settings.LASTFM_USER)
    scrobbles = user.get_recent_tracks(
        limit=1000, time_from=timestamp
    )
    save_scrobbles(scrobbles)


def scrobble_record(record, when):
    """
    Given a record and a datetime of when it started playing, scrobble
    it on last.fm
    """
    start_time = time.mktime(when.timetuple())
    tracks = []

    for track in record.track_set.all():
        track_data = {
            'artist'   : record.artist.first().name,
            'title'    : track.title,
            'album'    : record.title,
        }

        for datatype in track_data:
            val = track_data[datatype]
            if val in LASTFM_PRE_SUBMIT_SUBS[datatype]:
                track_data[datatype] = LASTFM_PRE_SUBMIT_SUBS[datatype][val]

        track_data['timestamp'] = start_time
        tracks.append(track_data)

        if track.duration:
            mins, secs = track.duration.split(':')
            seconds = int(secs) + (int(mins) * 60)
            start_time += seconds
        else:
            start_time += (3 * 60) + 41

    print(tracks)
    api.scrobble_many(tracks)


"""
Graphs
"""

def scrobbles_by_year_for_queryset(queryset):
    # In memory grouping
    scrobbles = collections.defaultdict(int)

    for scrobble in queryset:

        year = scrobble.datetime.year
        scrobbles[year] += 1

    by_year = sorted(
        [[y, c] for y, c in scrobbles.items()], key=lambda x: x[0]
    )

    if scrobbles:
        max_count = max(scrobbles.values())

        for group in by_year:
            perc = int(100 * (group[1] / float(max_count)))
            group.append(perc)

    by_year.reverse()
    return by_year


def total_scrobbles_by_year():
    by_year = Scrobble.objects.all().order_by('timestamp')
    first = by_year.first().datetime.year
    last = by_year.last().datetime.year
    counts = []

    for i in range(first, (last + 1)):

        start = datetime.datetime(i, 1, 1, 0, 0, 0)
        end   = datetime.datetime(i, 12, 31, 23, 59, 59)

        counts.append(
            [i, Scrobble.objects.filter(
                datetime__gte=start,
                datetime__lte=end
            ).count()]
        )

    counts.reverse()
    max_count = max([c[1] for c in counts])

    for group in counts:
        perc = int(100 * (group[1] / float(max_count)))
        group.append(perc)

    return counts
