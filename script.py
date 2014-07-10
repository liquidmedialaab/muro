# -*- coding: utf-8; -*-
import json
import urllib
import time
import twitter as twitter_backend
from operator import itemgetter
from datetime import datetime
from settings import config

def timestamp(dt):
    return 1000 * time.mktime(dt.timetuple())


def twitter(tag, conf):
    name = 'Twitter'
    client = twitter_backend.Twitter(
        auth=twitter_backend.OAuth(
            conf['access_token'], conf['access_token_secret'],
            conf['consumer_key'], conf['consumer_secret'])
    )

    params = {
        'q': '#'+tag,
        'count': 100,
        'include_entities': True,
        'result_type': 'mixed'
    }

    items = []

    print 'Retrieving twitter data...'

    response = client.search.tweets(**params)
    statuses = response['statuses']

    for item in statuses:
        # Sanity check to proceed retrieving things
        if not 'media' in item['entities']:
            continue

        # Building the Media item that will be added to the return list
        items.append({
            'media_provider': name.lower(),
            'media_type': 'image',
            'content': item['entities']['media'][0]['media_url'],
            'thumb': item['entities']['media'][0]['media_url'],
            'author': item['user']['name'],
            'width': item['entities']['media'][0]['sizes']['small']['w'],
            'height': item['entities']['media'][0]['sizes']['small']['h'],
            'original_url': item['entities']['media'][0]['expanded_url'],
            'date_posted': timestamp(datetime.strptime(
                item['created_at'],
                "%a %b %d %H:%M:%S +0000 %Y")),
        })
    return items


def instagram(tag, api_key):
    name = 'Instagram'
    api_url = (
        'https://api.instagram.com/'
        'v1/tags/{0}/media/recent?count=100&client_id={1}'.format(tag, api_key))

    items = []
    data = []

    print 'Retrieving instagram data from: '

    for i in range(1,4):
        print api_url
        response = json.load(urllib.urlopen(api_url))
        data = ( data + response['data'])
                
        if not 'next_url' in response['pagination']:
            break

        if (api_url == response['pagination']['next_url']):
            break

        api_url = response['pagination']['next_url']


    

    for item in data:
        items.append({
            'media_provider': name.lower(),
            'media_type': 'image',
            'content': item['images']['standard_resolution']['url'],
            'thumb': item['images']['thumbnail']['url'],
            'author': item['user']['username'],
            'width': item['images']['standard_resolution']['width'],
            'height': item['images']['standard_resolution']['height'],
            'original_url': item['link'],
            'date_posted': timestamp(datetime.fromtimestamp(
                float(item['created_time']))),
        })
    return items


def flickr(tag, api_key):
    name = 'Flickr'
    api_url = 'https://api.flickr.com/services/rest/'

    items = []

    params = {
        'method': 'flickr.photos.search',
        'api_key': api_key,
        'text': tag,
        'per_page': 500,
        'format': 'json',
        'nojsoncallback': 1,
        'extras': 'owner_name,date_upload,url_t,url_l',
    }

    url = '{0}?{1}'.format(api_url, urllib.urlencode(params))
    data = json.load(urllib.urlopen(url))

    print 'Retrieving flickr data from: '
    print url

    for item in data['photos']['photo']:
        # Sanity checks
        if 'url_l' not in item:
            continue

        items.append({
            'media_provider': name.lower(),
            'media_type': 'image',
            'content': item['url_l'],
            'thumb': item['url_t'],
            'author': item['ownername'],
            'width': item['width_l'],
            'height': item['height_l'],
            'original_url': 'http://www.flickr.com/photos/{0}/{1}'.format(
                item['owner'], item['id']),
            'date_posted': timestamp(datetime.fromtimestamp(
                float(item['dateupload']))),
        })

    return items


def picasa(tag):
    name = 'Picasa'
    api_url = 'https://picasaweb.google.com/data/feed/base/all'
    items = []

    params = {
        'alt': 'json',
        'kind': 'photo',
        'access': 'public',
        'filter': 1,
        'imgmax': 1600,
        'hl': 'pt_BR',
        'q': tag,
    }

    url = '{0}?{1}'.format(api_url, urllib.urlencode(params))
    data = json.load(urllib.urlopen(url))

    print url

    try:
        for item in data['feed']['entry']:
            # ignore malformed
            try: 
                items.append({
                    'media_provider': name.lower(),
                    'media_type': 'image',
                    'content': item['content']['src'],
                    'thumb': None,
                    'author': [x['name']['$t'] for x in item['author']],
                    'width': 0,
                    'height': 0,
                    'original_url': [x['href'] for x in item['link']][2],
                    'date_posted': timestamp(datetime.strptime(
                        item['published']['$t'], "%Y-%m-%dT%H:%M:%S.000Z")),
                })
            except:
                continue
        return items
    except KeyError:
        # no images found
        return []



def youtube(tag):
    name = 'Youtube'
    api_url = (
        'http://gdata.youtube.com'
        '/feeds/api/videos/-/{0}?alt=json'.format(tag))

    items = []
    data = json.load(urllib.urlopen(api_url))

    print 'Retrieving youtube data from:'
    print api_url

    try:
        for item in data['feed']['entry']:
            items.append({
                'media_provider': name.lower(),
                'media_type': 'video',
                'content': item['media$group']['media$content'][0]['url'],
                'thumb': item['media$group']['media$thumbnail'][0]['url'],
                'author': item['author'][0]['name']['$t'],
                'width': item['media$group']['media$thumbnail'][0]['width'],
                'height': item['media$group']['media$thumbnail'][0]['height'],
                'original_url': item['link'][0]['href'],
                'date_posted': timestamp(datetime.strptime(
                    item['updated']['$t'], "%Y-%m-%dT%H:%M:%S.000Z")),
            })
        
        return items
    except KeyError:
        # no videos found
        return []


def removeIgnored(original_items):

    api_url = (
        'https://spreadsheets.google.com/feeds/list/{0}'.format(config['gdocs_sheet']) +
        '/od6/public/values?alt=json')

    links = []
    items = []
    data = json.load(urllib.urlopen(api_url))

    try:
        # get links from gdocs
        for link in data['feed']['entry']:
            links.append(str(link['gsx$links']['$t']))

        # check if item is in ignore list
        for item in original_items:
            if item['original_url'] not in links:
                items.append(item)

        return items

    except KeyError:
        # there is no link in ignore list other error
        return original_items





def rockndroll():
    tags = config['tags']
    data = []

    for tag in tags:
        data = (
            flickr(tag, config['flickr_apikey']) +
            twitter(tag, config['twitter']) +
            instagram(tag, config['instagram_apikey']) +
            picasa(tag) +
            youtube(tag) +
            data
        )


    data = removeIgnored(data)

    data = sorted(data, key=itemgetter('date_posted'), reverse=True)

    # remove duplicates
    seen_urls = set()
    nodups = []
    for obj in data:
        if obj['original_url'] not in seen_urls:
            nodups.append(obj)
            seen_urls.add(obj['original_url'])
    data = nodups

    print len(data)

    with open(config['webpath'] + '/data.json',
'w') as f:
        f.write(json.dumps(data))

    


if __name__ == '__main__':
    rockndroll()
