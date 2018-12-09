## In a silent way

Managing Discogs collection, srobbling vinyl listening to last.fm

### Usage

Download collection:

```shell
./shhh download
```

Select a random record:

```shell
./shhh random
```

Select a random record from a genre:

```shell
./shhh random -g $GENRE
```

Scrobble records

```shell
./shhh scrobble
```

### Setup

File in `./inasilentway/settings.py`

Should contain:

```python
LASTFM_API_KEY = 'your api key'
LASTFM_SECRET  = 'your secret'
LASTFM_USER    = 'your username'
LASTFM_PASS    = md5('your password')
```
