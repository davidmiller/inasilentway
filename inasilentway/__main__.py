"""
Commandline entrypoint
"""
import argparse
import sys

from inasilentway import collection, last

def parse_args():
    parser = argparse.ArgumentParser(
        description='Choose a random record from discogs'
    )
    subparsers = parser.add_subparsers(help='Commands')

    parser_choose = subparsers.add_parser('random')
    parser_choose.set_defaults(func=collection.random_record)
    parser_choose.add_argument('-g', '--genre', help='Limit the choice to one with this genre')
    parser_choose.add_argument('-v', '--vinylscrobbler',
                               help='Open Vinyl Scrobbler', action='store_true')

    parser_shell = subparsers.add_parser('shell')
    parser_shell.set_defaults(func=collection.collection_shell)

    parser_download = subparsers.add_parser('download')
    parser_download.set_defaults(func=collection.download)

    parser_scrobble = subparsers.add_parser('scrobble')
    parser_scrobble.set_defaults(func=last.scrobble)

    parser_load_django = subparsers.add_parser('load_django')
    parser_load_django.set_defaults(func=collection.load_django)

    parser_scrobbles = subparsers.add_parser('load_scrobbles')
    parser_scrobbles.set_defaults(func=last.load_scrobbles)

    parser_scrobbles = subparsers.add_parser('link_scrobbles')
    parser_scrobbles.set_defaults(func=last.link_scrobbles)

    args = parser.parse_args()
    return args

def main():
    args = parse_args()

    args.func(args)
    return 0

if __name__ == '__main__':
    sys.exit(main())
