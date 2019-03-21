"""
Management command for inasilentway
"""
from django.core.management.base import BaseCommand

from inasilentway import discogs, lastfm


class Command(BaseCommand):
    """
    Commandline entrypoint for initial load of data into the application
    """
    def handle(*args, **kwargs):
        print("Loading Discogs Collection")
        discogs.load_collection()

        # print("Loading Last.fm Scrobble History")
        # lastfm.load_scrobble_history()
