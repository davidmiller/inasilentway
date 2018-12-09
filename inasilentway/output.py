"""
Printing utilities
"""
import webbrowser

def print_record(record, genre=False):
    print u'{title} - {artists} ({year})'.format(
        title=record.release.title,
        artists=' '.join([a.name for a in record.release.artists]),
        year=record.release.year
    )
    if genre:
        print ' '.join(record.release.genres)
    return

def open_vnylscrobbler(record):
    vinylscrobbler_url = 'http://vinylscrobbler.com/search?q={0}'.format(
        record.release.title
    )
    webbrowser.open(vinylscrobbler_url)
    return
