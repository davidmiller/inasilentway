"""
Management command to refresh recent scrobbles
"""
from django.core.management.base import BaseCommand

from inasilentway import lastfm


class Command(BaseCommand):
    """
    Commandline entrypoint for initial load of data into the application
    """
    def handle(*args, **kwargs):
        print("Loading Last.fm Scrobble History")
        lastfm.load_last_24_hours_of_scrobbles()
