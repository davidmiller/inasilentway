"""
Management command to attempt to link unlinked scrobbles in case we've gotten
cleverer at linking them since we last tried.
"""
import sys

from django.core.management.base import BaseCommand

from inasilentway import models, lastfm


class Command(BaseCommand):
    """
    Pull all scrobbles without a match and then attempt to link them.
    """
    def report_unlinked_count(self):
        """
        Print a report of how many unlinked scrobbles we have
        """
        unlinked = models.Scrobble.objects.filter(isw_track__isnull=True)
        count = unlinked.count()
        print('{} unlinked Scrobbles'.format(count))
        return count

    def handle(self, *a, **k):
        print("Starting status:")
        start = self.report_unlinked_count()

        print("Starting link attempt")
        unlinked = models.Scrobble.objects.filter(isw_track__isnull=True)
        for i, scrobble in enumerate(unlinked):
            lastfm.link_scrobble(scrobble)
            if i % 50 == 0:
                sys.stdout.write('.')
            if i % 2000 == 0:
                sys.stdout.write('{}\n'.format(i))

        print("Attempt finished")
        print("New status:")
        end = self.report_unlinked_count()
        print('({})'.format(start - end))
