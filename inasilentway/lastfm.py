"""
Interacting with Last.fm from Inasilentway
"""
import collections
import datetime
import time

from django.conf import settings
from django.utils import timezone
import pylast
from pytz.tzinfo import NonExistentTimeError

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
# Some records have additional tracks in the Discogs listing - for instance a
# bonus CD, or a 'track' for the title of a side of an album. Wwhen this
# happens we exclude them, for now with hard coded Track.exclude() criteria.
#
LASTFM_PRE_SUBMIT_TRACKS = {
    # Title:Artist.first().name : {method: {**kwargs}}
    'Wave:Antonio Carlos Jobim': [{'exclude': {'position__startswith': 'CD'}}],
    'It Takes A Nation Of Millions To Hold Us Back:Public Enemy': [{'exclude': {'title__icontains': 'side'}}],
    'Live At Carnegie Hall:Ryan Adams': [{'exclude': {'title': 'Untitled'}}, {'exclude': {'title__contains': 'November'}}],
    'Mess:Liars': [{'exclude': {'position__startswith': 'CD'}}],
    'O Amor, O Sorriso E A Flor:João Gilberto': [{'exclude': {'position__startswith': 'CD'}}],
    'Bad As Me:Tom Waits': [{'exclude': {'position__startswith': 'CD'}}],
    'Yankee Hotel Foxtrot:Wilco': [{'exclude': {'position__startswith': 'CD'}}],
    'Ballads:The John Coltrane Quartet': [{'exclude': {'position': ''}}],
    'Ghosteen:Nick Cave & The Bad Seeds': [{'exclude': {'position': ''}}],
    'Are You Experienced / Axis: Bold As Love:The Jimi Hendrix Experience': [{'exclude': {'position': ''}}],
    'The Modern Jazz Quartet:The Modern Jazz Quartet': [{'exclude': {'position': ''}}],
    'Chapter Four: Alive In New York:Gato Barbieri': [{'exclude': {'position': ''}}],
    'Bird / The Savoy Recordings (Master Takes):Charlie Parker': [{'exclude': {'position': ''}}],
    'Memorial:Clifford Brown': [{'exclude': {'position': ''}}],
    'Misterioso:The Thelonious Monk Quartet': [{'exclude': {'title__icontains': 'bonus'}}],
    '... And Star Power:Foxygen': [{'exclude': {'position': ''}}],
    "This One's For Blanton:Duke Ellington": [{'exclude': {'position': ''}}],
    "Africa / Brass:The John Coltrane Quartet": [{'exclude': {'position': ''}}],
    "Highlights From La Damnation De Faust:Hector Berlioz": [{'exclude': {'position': ''}}],
    "Automatic For The People:R.E.M.": [{'exclude': {'position': ''}}],
    "A Drum Is A Woman:Duke Ellington And His Orchestra": [{'exclude': {'position': ''}}],
    "Ellington At Newport:Duke Ellington And His Orchestra": [{'exclude': {'position': ''}}],
    "Bossa Nova!:João Gilberto": [{'exclude': {'position__startswith': 'CD'}}],
    "Absolutely Free:The Mothers": [{'exclude': {'position': ''}}],
    "Imitations:Mark Lanegan": [{'exclude': {'position__startswith': 'CD'}}],
    "Journey To The Mountain Of Forever:Binker And Moses": [{'exclude': {'position': ''}}],
    'Sings The Cole Porter Songbook:Ella Fitzgerald': [{'exclude': {'position': ''}}],
    'Ruth Is Stranger Than Richard:Robert Wyatt': [{'exclude': {'position': ''}}],
    'Centipede Hz:Animal Collective': [{'exclude': {'position__startswith': 'DVD'}}],
    "IX:...And You Will Know Us By The Trail Of Dead": [{'exclude': {'position__startswith': 'CD'}}],
    'Comicopera:Robert Wyatt': [{'exclude': {'position': ''}}],
    'Enter The Wu-Tang (36 Chambers):Wu-Tang Clan': [{'exclude': {'position': ''}}],

}

# Sometimes we would like to pick an artist from a record that has many.

# e.g. Discogs lists Earl Hines as the first artist on The Louis Armstrong
# Story vol 3. Louis Armstrong and Earl Hines. With love, Earl is not why we're here.
LASTFM_PRE_SUBMIT_ARTIST_CHOICES = {
    'The Louis Armstrong Story - Vol. 3': 'Louis Armstrong',
    'The Greatest Trumpet Of Them All'  : 'The Dizzy Gillespie Octet',
    'Things Are Getting Better'         : 'Cannonball Adderley',
    'Oleo'                              : 'Grant Green Quartet',
    'In Orbit'                          : 'Clark Terry',
    'Der Ring Des Nibelungen'           : 'Richard Wagner',
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
        # lastfm name                                           : disgogs name
        'Desafinado: Bossa Nova & Jazz Samba'                   : 'Desafinado Coleman Hawkins Plays Bossa Nova & Jazz Samba', # noqa
        'Oscar Peterson Plays the Duke Ellington Songbook'      : 'The Duke Ellington Songbook', # noqa
        'Standard Time Vol.2 - Intimacy Calling'                : 'Standard Time Vol. 2 (Intimacy Calling)', # noqa
        'White Light/White Heat'                                : 'White Light / White Heat', # noqa
        'Thelonious Monk Plays Duke Ellington'                  : 'Plays Duke Ellington', # noaa
        'Nights Of Ballads & Blues'                             : 'Nights Of Ballads And Blues', # noqa
        'Birth of the Cool'                                     : 'The Birth Of The Cool', # noqa
        'The Ace Of Rhythm'                                     : 'The Ace Of Rhythm ', # Discogs leaves in trailing spaces on album names :/
        'Soused'                                                : 'Soused ',
        'Your Queen Is a Reptile'                               : 'Your Queen Is A Reptile ',
        'Muito À Vontade'                                       : 'Muito à Vontade',
        'A Night At Birdland, Volume 1'                         : 'A Night At Birdland Volume 1',
        'A Night at Birdland, Volume 2'                         : 'A Night At Birdland Volume 2',
        'Out to Lunch'                                          : 'Out To Lunch! ',
        'Out to Lunch!'                                         : 'Out To Lunch! ',
        'A New Morning, Changing Weather'                       : 'A New Morning Changing Weather',
        '"Classical" Symphony / Symphony No 1'                  :'"Classical" Symphony / Symphony No 1 ',
        'Genius of Modern Music, Volume 1'                      : 'genius of modern music volume one',
        'Genius Of Modern Music: Vol. 1'                        : 'genius of modern music volume one',
        'The Complete Jelly Roll Morton Volumes 7/8 (1930-1940)': 'The Complete Jelly Roll Morton Volumes 7/8 (1930-1940) ',
        '…And Star Power'                                       : '... And Star Power',
        '801 / 801 Live'                                        : '801 Live',
        'Blood on the Tracks'                                   : 'Blood On The Tracks',
        'Master Takes. The Savoy Recordings'                    : 'Master Takes / The Savoy Recordings',
        'Ella Fitzgerald Sings the Cole Porter Song Book'       : 'Sings The Cole Porter Songbook',
        'Ella Fitzgerald Sings The Cole Porter Songbook'        : 'Sings The Cole Porter Songbook',
        'Live At The Village Vanguard'                          : '"Live" At the Village Vanguard',
    },

    'artist': {
        # lastfm name                         : discogs name
        'Duke Ellington & His Orchestra'      : 'Duke Ellington And His Orchestra',
        'Miles Davis Quintet'                 : 'The Miles Davis Quintet',
        'Clifford Brown & Max Roach'          : 'Clifford Brown And Max Roach',
        'Antônio Carlos Jobim'                : 'Antonio Carlos Jobim',
        'N.W.A'                               : 'N.W.A.',
        'Mark Lanegan'                        : 'Mark Lanegan Band',
        'Oscar Peterson Trio'                 : 'The Oscar Peterson Trio',
        'Miles Davis'                         : 'Miles Davis All Stars', # Walkin'
        'Miles Davis Quintet'                 : 'The Miles Davis Quintet', # Cookin'
        'The Miles Davis Quartet'             : 'Miles Davis', # The Musings Of Miles
        'Bill Evans Trio'                     : 'The Bill Evans Trio',
        'Bill Evans'                          : 'The Bill Evans Trio',
        'Modern Jazz Quartet'                 : 'The Modern Jazz Quartet',
        'Duke Ellington'                      : 'Duke Ellington And His Orchestra',
        'Captain Beefheart & His Magic Band'  : 'Captain Beefheart And His Magic Band',
        'The (International) Noise Conspiracy': 'The International Noise Conspiracy',
        'Sonny Rollins'                       : 'Sonny Rollins Quartet',
        'Thelonious Monk'                     : 'The Thelonious Monk Orchestra',
        'Thelonious Monk'                     : 'Thelonious Monk Septet',
        'Phil Manzanera'                      : '801',
        'HAIM'                                : 'Haim (2)',

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

try:
    api = pylast.LastFMNetwork(
        api_key=settings.LASTFM_API_KEY,
        api_secret=settings.LASTFM_SECRET,
        username=settings.LASTFM_USER,
        password_hash=settings.LASTFM_PASS
    )
except pylast.NetworkError:
    print('No network available')
except AttributeError:
    print('No Last.fm API details')
    api = None

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


def _match_track(album, title):
    """
    Given a record and a track name, discover if there
    is a matching track
    """
    for track in album.track_set.all():
        if track.title.lower().strip() == title.lower().strip():
            return track


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
        for album in album_matches:
            track = _match_track(album, title)
            if track:
                match_album = album
                match_track = track
                break
    else:
        match_track = _match_track(match_album, title)

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
    return match(str(scrobble.artist), str(scrobble.album), str(scrobble.title))


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
        try:
            scrob.datetime = timezone.make_aware(
                datetime.datetime.strptime(scrobble.playback_date, format_string)
            )
        except NonExistentTimeError:
            pass # We get this from last.fm when we play things while clocks
                 # change
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
    # This is actually the most recent 300 - useful for
    # when the get scrobbles API is erroring / timing out

    now = timezone.make_aware(datetime.datetime.now())
    yesterday = now - datetime.timedelta(days=1)
    timestamp = time.mktime(now.timetuple())
    user = api.get_user(settings.LASTFM_USER)
    scrobbles = user.get_recent_tracks(
        limit=300, time_to=timestamp
    )
    save_scrobbles(scrobbles)

    # This is 'get the most recent 1K scrobbles in the last 3 days

    # now = timezone.make_aware(datetime.datetime.now())
    # yesterday = now - datetime.timedelta(days=1)
    # timestamp = time.mktime(yesterday.timetuple())
    # user = api.get_user(settings.LASTFM_USER)
    # scrobbles = user.get_recent_tracks(
    #     limit=1000, time_from=timestamp
    # )
    # save_scrobbles(scrobbles)


def prepare_artist(record):
    """
    Sometimes we would like to pick an artist from a record
    that has many.

    e.g. Discogs lists Earl Hines as the first artist on
    The Louis Armstrong Story vol 3. Louis Armstrong and Earl Hines.
    With love, Earl is not why we're here.
    """
    if record.title in LASTFM_PRE_SUBMIT_ARTIST_CHOICES:
        decision = LASTFM_PRE_SUBMIT_ARTIST_CHOICES[record.title]
        if decision in [a.name for a in record.artist.all()]:
            return decision
    return record.artist.first().name


def prepare_tracks(tracks, artist, title, when):
    """
    Given an iterable of tracks to submit, the name of the artist,
    the name of the album and a start datetime
    prepare them for scrobbling.
    """
    prepared_tracks = []

    start_time = time.mktime(when.timetuple())

    for track in tracks:
        track_data = {
            'artist'   : artist,
            'title'    : track.title,
            'album'    : title,
        }

        for datatype in track_data:
            val = track_data[datatype]
            if val in LASTFM_PRE_SUBMIT_SUBS[datatype]:
                track_data[datatype] = LASTFM_PRE_SUBMIT_SUBS[datatype][val]

        track_data['timestamp'] = start_time
        prepared_tracks.append(track_data)

        if track.duration:
            mins, secs = track.duration.split(':')
            seconds = int(secs) + (int(mins) * 60)
            start_time += seconds
        else:
            start_time += (3 * 60) + 41

    for track in prepared_tracks:
        print(track)

    return prepared_tracks


def scrobble_tracks(tracks, date):
    prepared_tracks = prepare_tracks(
        tracks,
        tracks[0].record.artist.first().name,
        tracks[0].record.title,
        date
    )
    api.scrobble_many(prepared_tracks)
    return


def scrobble_record(record, when):
    """
    Given a record and a datetime of when it started playing, scrobble
    it on last.fm
    """
    print('Scrobbling record started')
    t1 = time.time()

    artist = prepare_artist(record)
    track_set = record.track_set.all()

    # auto filtering of tracks e.g. bonus CDs
    combined = ':'.join([record.title, artist])
    if combined in LASTFM_PRE_SUBMIT_TRACKS:
        for criteria in LASTFM_PRE_SUBMIT_TRACKS[combined]:
            for method, args in  criteria.items():
                meth = getattr(track_set, method)
                print('{} {}'.format(str(meth), args))
                track_set = meth(**args)

    tracks = prepare_tracks(track_set, artist, record.title, when)

    # import logging
    # pylast.logger.setLevel(logging.DEBUG)
    # pylast.logger.addHandler(logging.StreamHandler())

    api.scrobble_many(tracks)

    apicall = time.time() - t1
    print('API call took {}s'.format(apicall))


def filter_tracks(record, tracks):
    """
    Given a record and a string to filter tracks by, return only
    the tracks that match the filter.
    """
    filtered_tracks = []
    filters = tracks.split(',')
    for condition in filters:
        # A*
        if condition.endswith('*'):
            if len(condition) == 2:
                filtered_tracks.append(
                    record.track_set.all().filter(
                        position__istartswith=condition[0]
                    )
                )
    results = []
    for queryset in filtered_tracks:
        results += list(queryset)
    return results



"""
Graphs
"""

def scrobbles_by_day_for_queryset(queryset, min_values=0):
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

    max_count = max([c[1] for c in counts])

    for group in counts:
        group.append(utils.percent_of(group[1], max_count))

    if len(counts) < min_values:
        days = [i+1 for i in range(min_values)]

        for d in days:
            if len(counts) < d:
                counts.append([d, 0, 0])

    counts.reverse()
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
