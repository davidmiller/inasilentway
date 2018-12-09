"""
Interact with Last.fm
"""
import datetime
import time
import sys

import parsedatetime
import pylast

from inasilentway import collection, output, settings

lastfm = pylast.LastFMNetwork(
    api_key=settings.LASTFM_API_KEY,
    api_secret=settings.LASTFM_SECRET,
    username=settings.LASTFM_USER,
    password_hash=settings.LASTFM_PASS
)


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


def scrobble_record(record, start):
    """
    Scrobble a single record starting at x
    """
    tracks = []
    for track in record.release.tracklist:
        tracks.append(
            (
                record.release.artists[0].name,
                track.title,
                start
            )
        )
        if track.duration:
            mins, secs = track.duration.split(':')
            seconds = int(secs) + (int(mins) * 60)
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

    for track in tracks:
        lastfm.scrobble(*track)
        sys.stdout.write('.')
        sys.stdout.flush()

    sys.stdout.write('\n')
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
