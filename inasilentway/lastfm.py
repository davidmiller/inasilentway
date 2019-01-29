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
from inasilentway import utils

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

#
# Some records have additional tracks - for instance a 'bonus CD' or
# '45 when this happens we exclude them, for now with hard coded Track.exclude()
# criteria. Later we expect to be able to specify either sides or tracks in the
# UI itself.
#
LASTFM_PRE_SUBMIT_TRACKS = {
    # Title:Artist.first().name : {method: {**kwargs}}
    'Wave:Antonio Carlos Jobim': {'exclude': {'position__startswith': 'CD'}},
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
        # lastfm name                                     : disgogs name
        'Desafinado: Bossa Nova & Jazz Samba'             : 'Desafinado Coleman Hawkins Plays Bossa Nova & Jazz Samba', # noqa
        'Oscar Peterson Plays the Duke Ellington Songbook': 'The Duke Ellington Songbook', # noqa
        'Standard Time Vol.2 - Intimacy Calling'          : 'Standard Time Vol. 2 (Intimacy Calling)', # noqa
        'White Light/White Heat'                          : 'White Light / White Heat', # noqa
        'Thelonious Monk Plays Duke Ellington'            : 'Plays Duke Ellington', # noaa
        'Nights Of Ballads & Blues'                       : 'Nights Of Ballads And Blues', # noqa
        'Birth of the Cool'                               : 'The Birth Of The Cool' # noqa
    },

    'artist': {
        # lastfm name                   : discogs name
        'Duke Ellington & His Orchestra': 'Duke Ellington And His Orchestra',
        'Miles Davis Quintet'           : 'The Miles Davis Quintet',
        'Clifford Brown & Max Roach'    : 'Clifford Brown And Max Roach',
        'Antônio Carlos Jobim'          : 'Antonio Carlos Jobim',
        'N.W.A'                         : 'N.W.A.',
        'Mark Lanegan'                  : 'Mark Lanegan Band',
        'Oscar Peterson Trio'           : 'The Oscar Peterson Trio',
        'Miles Davis'                   : 'Miles Davis All Stars', # Walkin'
        'Miles Davis Quintet'           : 'The Miles Davis Quintet', # Cookin'
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
        return None

    if len(artist_matches) == 1:
        return artist_matches[0]

    if len(artist_matches) > 1:
        import pdb; pdb.set_trace() # noqa
        print(artist_matches)


def _match(artist, album, title):
    """
    Return matches if we have them or none
    e.g. (The Hives, Veni Vidi Viscious, Main Offender)
    or (None, None, None)
    """
    from inasilentway.models import Record

    match_album = None
    match_track = None

    matching_artist = match_artist(artist)

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
        if track.title.lower().strip() == title.lower().strip():
            match_track = track

    return matching_artist, match_album, match_track


def match(artist, album, title):
    """
    Given an ARTIST, ALBUM and track TITLE for a Last.fm scrobble,
    match it against a Discogs record in our collection.

    Run the match queries multiple times if no matches are found but
    there are corrections found in our hard coded list.
    """

    if album in LASTFM_CORRECTIONS['album']:
        album = LASTFM_CORRECTIONS['album'][album]

    matching = _match(artist, album, title)

    if all(matching):
        return matching

    if artist in LASTFM_CORRECTIONS['artist']:
        artist = LASTFM_CORRECTIONS['artist'][artist]

        matching = _match(artist, album, title)

    return matching


def match_scrobble(scrobble):
    """
    Given a Scrobble, match it against our Discogs collection.

    (Shorthand function to avoid having to split parameters to match() )
    """
    return match(scrobble.artist, scrobble.album, scrobble.title)


def link_scrobble(scrobble):
    """
    Given a scrobble, link it to an artist, track and record
    """
    matches = match_scrobble(scrobble)
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
    print('Scrobbling record started')
    t1 = time.time()
    start_time = time.mktime(when.timetuple())
    tracks = []
    artist = record.artist.first().name
    track_set = record.track_set.all()

    combined = ':'.join([record.title, artist])

    if combined in LASTFM_PRE_SUBMIT_TRACKS:
        for method, args in LASTFM_PRE_SUBMIT_TRACKS[combined].items():
            meth = getattr(track_set, method)
            track_set = meth(**args)

    for track in track_set:
        track_data = {
            'artist'   : artist,
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

    for track in tracks:
        print(track)

    api.scrobble_many(tracks)

    apicall = time.time() - t1
    print('API call took {}s'.format(apicall))


"""
Graphs
"""

def scrobbles_by_day_for_queryset(queryset):
    if queryset.count() == 0:
        return []

    queryset = queryset.order_by('timestamp')
    last  = queryset.last().ts_as_dt()
    counts = []

    for i in range(1, (last.day +1)):
        start = time.mktime(
            datetime.datetime(last.year, last.month, i, 0, 0, 0).timetuple()
        )
        end   = time.mktime(
            datetime.datetime(last.year, last.month, i, 23, 59, 59).timetuple()
        )

        counts.append(
            [i, queryset.filter(
                timestamp__gte=start,
                timestamp__lte=end
            ).count()]
        )

    counts.reverse()
    max_count = max([c[1] for c in counts])

    for group in counts:
        group.append(utils.percent_of(group[1], max_count))

    return counts


def scrobbles_by_month_for_queryset(queryset):
    if queryset.count() == 0:
        return []

    queryset = queryset.order_by('timestamp')
    first  = queryset.first().ts_as_dt()
    counts = []

    for i in range(1, 13):
        start = time.mktime(
            datetime.datetime(first.year, i, 1, 0, 0, 0).timetuple()
        )

        if i == 12:
            end = time.mktime(
                datetime.datetime((first.year + 1), 1, 1, 0, 0).timetuple()
            )
        else:
            end   = time.mktime(
                datetime.datetime(first.year, (i + 1), 1, 0, 0).timetuple()
            )

        counts.append(
            [i, queryset.filter(
                timestamp__gte=start,
                timestamp__lt=end
            ).count()]
        )

    counts.reverse()
    max_count = max([c[1] for c in counts])

    print(counts)

    for group in counts:
        group.append(utils.percent_of(group[1], max_count))

    return counts


def scrobbles_by_year_for_queryset(queryset):
    if queryset.count() == 0:
        return []
    queryset = queryset.order_by('timestamp')
    first = queryset.first().datetime.year
    last  = queryset.last().datetime.year
    counts = []

    for i in range(first, (last +1)):
        start = datetime.datetime(i, 1, 1, 0, 0, 0)
        end   = datetime.datetime(i, 12, 31, 23, 59, 59)

        counts.append(
            [i, queryset.filter(
                datetime__gte=start,
                datetime__lte=end
            ).count()]
        )

    counts.reverse()
    max_count = max([c[1] for c in counts])

    for group in counts:
        group.append(utils.percent_of(group[1], max_count))

    return counts


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
