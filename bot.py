import common
import argparse
import random
import sys
import feedparser
import time
import os
from mastodon import Mastodon

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    args = parser.parse_args()
    
    timestamp = int(time.time())
    config = common.read_json(args.filename)
    assert(config is not None)
    data = common.read_json(config['datafile'])

    feed_list = config['feed_list']

    # init data
    if data is None:
        data = {}
    if 'feed_data_dict' not in data:
        data['feed_data_dict'] = {}
    if 'entry_data_dict' not in data:
        data['entry_data_dict'] = {}
    for feed in feed_list:
        feed_id = feed['id']
        if feed_id not in data['feed_data_dict']:
            data['feed_data_dict'][feed_id] = {}
        if 'last_refresh' not in data['feed_data_dict'][feed_id]:
            data['feed_data_dict'][feed_id]['last_refresh'] = 0

    # select feed
    feed_list = config['feed_list']
    random.shuffle(feed_list)
    
    def refresh_filter(feed):
        feed_id = feed['id']
        last_refresh = data['feed_data_dict'][feed_id]['last_refresh']
        if last_refresh <= timestamp - config['min_refresh_sec']:
            return True
    feed_list = filter(refresh_filter,feed_list)

    feed_list = list(feed_list)
    feed_list = feed_list[:config['operate_feed_count']]

    if len(feed_list) == 0:
        sys.exit(0)

    # output feed data

    for feed in feed_list:
        feed_id = feed['id']
        
        mm = Mastodon(
            api_base_url = feed['mastodon_account']['api_base_url'],
            client_id = feed['mastodon_account']['client_id'],
            client_secret = feed['mastodon_account']['client_secret'],
            access_token = feed['mastodon_account']['access_token']
        )
        
        fp = feedparser.parse(feed['feed_source']['url'])
        for feed_entry in reversed(fp.entries):
            feed_entry_id = feed_entry.id
            entry_data_id = '{0}|{1}'.format(feed_id, feed_entry_id)
            if entry_data_id in data['entry_data_dict']:
                continue

            feed_entry_text = feed_entry.summary

            #print(feed_entry.title)
            #print(feed_entry_text)
            #print(feed_entry.link)
            
            char_limit = config['char_limit']
            char_limit-=len(feed_entry.title)
            char_limit-=len(feed_entry.link)
            feed_entry_text = feed_entry_text[:char_limit]
            
            toot_text = '{0}\n\n{1}\n\n{2}'.format(feed_entry.title,feed_entry_text,feed_entry.link)
            mm.toot(toot_text)

            data['entry_data_dict'][entry_data_id] = {}
            data['entry_data_dict'][entry_data_id]['last_seen'] = timestamp
        data['feed_data_dict'][feed_id]['last_refresh'] = timestamp

    # forget old entry
    def should_remember(k,v):
        return v['last_seen'] >= timestamp-config['entry_remember_sec']
    data['entry_data_dict'] = {k:v for k,v in data['entry_data_dict'].items() if should_remember(k,v)}

    common.write_json(config['datafile'],data)
