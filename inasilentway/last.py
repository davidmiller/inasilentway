"""
Interact with Last.fm
"""
import collections
import datetime
import time
import sys

import parsedatetime
import pylast

from inasilentway import collection, output, utils

def get_lastfm():
    utils.setup_django()
    from django.conf import settings

    lastfm = pylast.LastFMNetwork(
        api_key=settings.LASTFM_API_KEY,
        api_secret=settings.LASTFM_SECRET,
        username=settings.LASTFM_USER,
        password_hash=settings.LASTFM_PASS
    )
    return lastfm


def select_record():
    """
    Select a record to scrobble
    """
    search_string = input('What would you like to scrobble? ')
    matches = collection.search(search_string)

    if len(matches) == 0:
        print("No matches found")
        return select_record()

    choices = ['[x] None of the above, return to search']
    for i, record in enumerate(matches):
        choices.append(u'[{}] {}'.format(i, output.format_record(record)))

    select_msg = "\n".join(choices)
    print(select_msg)
    selection = input('Choice: ')
    if selection == 'x':
        return select_record()
    index = int(selection)
    try:
        record = matches[index]
        print(u'You Chose {}'.format(output.format_record(record)))
        return record
    except KeyError:
        "Couldn't understand {}".format(selection)
        return

def get_timestamp():
    """
    When would you like to scrobble it ?
    """
    when = input('When was the scrobble? ')
    cal = parsedatetime.Calendar()
    time_struct, _ = cal.parse(when)
    timestamp = time.mktime(time_struct)
    as_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y %m %d %H:%M')
    print('Parsed as {} '.format(as_str))
    answer = input('Correct? [Y|N] ')
    if answer.lower() == 'y':
        return timestamp
    return get_timestamp()


def scrobble_django_record(record, when):
    # TODO: Rename this

    start_time = time.mktime(when.timetuple())
    tracks = []
    for track in record.track_set.all():
        tracks.append(
            {
                'artist'   : record.artist.first().name,
                'title'    : track.title,
                'album'    : record.title,
                'timestamp': start_time
            }
        )
        if track.duration:
            mins, secs = track.duration.split(':')
            seconds = int(secs) + (int(mins) * 60)
            start_time += seconds
        else:
            start_time += (3 * 60) + 41


    lastfm = get_lastfm()
#    raise ValueError()
    lastfm.scrobble_many(tracks)
 #   for track in tracks:
  #      print(track)

#    print('Would have scrobbled')


def scrobble_record(record, start):
    """
    Scrobble a single record starting at x

    TODO: Delete this !
    """
    tracks = []
    for track in record.release.tracklist:
        tracks.append(
            {
                'artist'   : record.release.artists[0].name,
                'title'    : track.title,
                'album'    : record.release.title,
                'timestamp': start
            }
        )
        if track.duration:
            mins, secs = track.duration.split(':')
            seconds = int(secs) + (int(mins) * 60)
            print(seconds)
            start += seconds
        else:
            start += (3 * 60) + 41

    print('Scrobbling:')
    for track in tracks:
        print('{}, {}, {}'.format(
            track[0],
            track[1],
            datetime.datetime.fromtimestamp(track[2]).strftime('%Y %m %d %H:%M')
        ))

    confirm = input('Make it so ? ([Y|N]) ')
    if confirm.lower() != 'y':
        print("Didn't read that as confirmation, bailing")
        return

    lastfm = get_lastfm()
    lastfm.scrobble_many(tracks)

    print('All done!')
    return scrobble(None)



def scrobble(args):
    """
    commandline entrypoint for scrobbling
    """
    record = select_record()
    if record is None:
        return
    timestamp = get_timestamp()
    scrobble_record(record, timestamp)


def get_scrobbles():
    """
    Get this user's scrobbles. All of them.
    """
    from django.conf import settings

    from inasilentway.models import Scrobble

    lastfm = get_lastfm()

    if Scrobble.objects.count() > 0:
        # oldest = Scrobble.objects.all().order_by('timestamp').first()
        # oldest_scrobble = oldest.timestamp
        newest = Scrobble.objects.all().order_by('timestamp').last()
        print(newest.title)
        newest_scrobble = newest.timestamp


    user = lastfm.get_user(settings.LASTFM_USER)
    tracks = user.get_recent_tracks(limit=1000, time_from=newest_scrobble)
    print(tracks)
    return tracks


def save_scrobbles(scrobbles):
    """
    Give some scrobbles, save them to the database
    """
    from inasilentway.models import Scrobble
    from django.utils import timezone

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


def save_scrobbles_since(when):
    from django.conf import settings

    lastfm = get_lastfm()
    user = lastfm.get_user(settings.LASTFM_USER)

    tracks = user.get_recent_tracks(limit=1000, time_from=time.mktime(when.timetuple()))
    save_scrobbles(tracks)


def load_scrobbles(args):
    """
    Commandline entrypoint to get scrobbles and print them (warning, big)
    """
    utils.setup_django()
    scrobbles = get_scrobbles()
    save_scrobbles(scrobbles)
    from inasilentway.models import Scrobble
    print('We have {} scrobbles'.format(Scrobble.objects.count()))
    if len(scrobbles) > 0:
        print('Going again')
        load_scrobbles(args)


def match(artist, album, title):
    """
    Return matches if we have them or none
    """
    from inasilentway.models import Record, Artist

    match_album = None
    match_track = None
    match_artist = None

    artist_matches = Artist.objects.filter(name__iexact=artist)

    if len(artist_matches) == 0:
        return match_artist, match_album, match_track

    if len(artist_matches) == 1:
        match_artist = artist_matches[0]

    if len(artist_matches) > 1:
        import pdb; pdb.set_trace()
        print(artist_matches)

    album_matches = Record.objects.filter(
        title__iexact=album,
        artist=match_artist
    )

    if len(album_matches) == 0:
        return match_artist, match_album, match_track

    if len(album_matches) == 1:
        match_album = album_matches[0]

    if len(album_matches) > 1:
        # E.g. Billie holiday with many "all or nothing at all" albums
        return match_artist, match_album, match_track

    for track in match_album.track_set.all():
        if track.title.lower() == title.lower():
            match_track = track

    return match_artist, match_album, match_track

def make_links(scrobbles):

    print('{} unlinked scrobbles'.format(scrobbles.count()))
    matches_added = 0


    for scrobble in scrobbles:
        artist, album, track = match(scrobble.artist, scrobble.album, scrobble.title)

        if track:
            scrobble.isw_track = track
        if artist:
            scrobble.isw_album = album
        if album:
            scrobble.isw_artist = artist

        if any([track, artist, album]):
            scrobble.save()

            matches_added += 1
            print('Matched saved')

        else:
            print('No matches, next')
            continue

    print('This run added {} scrobble matches'.format(matches_added))


def link_scrobbles(args):
    """
    Commandline entrypoint to get scrobbles and link them with
    records in our collection
    """
    utils.setup_django()

    from inasilentway.models import Scrobble, Record

    unlinked = Scrobble.objects.filter(
        isw_album__isnull=True,
        album__isnull=False
    )
    make_links(unlinked)
