#!/usr/bin/python3

import argparse
import os
import requests
import secrets
import sys
from datetime import datetime
import pprint
from urllib.parse import urlsplit, urlunsplit

'''
Call the MAAS api with the OAuth header.  Takes an endpoint, for example:

maasapi machines

(will add a trailing '/' to the path if none exists)

Put your api key in ~/maas-api-key, or someplace more secure
(inside a password manager, perhaps)
'''

APIKEY=open(os.path.expanduser('~/maas-api-key')).read().strip()

CONSUMER, TOKEN, SECRET = APIKEY.split(':')

def oauth_header(consumer, token, secret):
    nonce = secrets.token_urlsafe(16)
    timestamp = int(datetime.now().timestamp())
    return f'OAuth oauth_version="1.0", oauth_signature_method="PLAINTEXT", oauth_consumer_key="{consumer}", oauth_token="{token}", oauth_signature="&{secret}", oauth_nonce="{nonce}", oauth_timestamp="{timestamp}"'

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('-X', help='http method', default='GET')
    ap.add_argument('-d', '--data', help='form data (if any), k1=v1;k2=v2')
    ap.add_argument('-s', '--server', help='MAAS server', default='soko02.front.sepia.ceph.com')
    ap.add_argument('-v', '--verbose', help='show request', action='store_true')
    ap.add_argument('-V', '--version', help='api version', default='2.0')
    ap.add_argument('endpoint', help='API endpoint')
    return ap.parse_args()

def do_request(method, url, headers=None, data=None, verbose=False):
    if headers is None:
        headers={
            'Authorization' : oauth_header(CONSUMER, TOKEN, SECRET),
            'Accept' : 'application/json',
        }
    req = requests.Request(
        method=method,
        url=url,
        headers=headers,
        data=data,
    )
    if verbose:
        pprint.pprint(req.__dict__, stream=sys.stderr)
    try:
        resp = requests.Session().send(req.prepare())
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        resp = e.response
        if verbose:
            print(f'{url}: {resp.status_code} {resp._content.decode()}', file=sys.stderr)
        else:
            print(f'{url}: {resp.status_code} {resp.reason}', file=sys.stderr)
        return False, ""
    return True, resp

def main():
    args = parse_args()
    ep = urlsplit(args.endpoint)
    # add a / if it needs it
    newpath = ep.path
    if newpath[-1] != '/':
        newpath += '/'
    ep = urlunsplit(('', '', newpath, ep.query, ep.fragment))

    datadict = None
    if args.data:
        datadict = dict()
        for datum in args.data.split(';'):
            dk, dv = datum.split('=')
            datadict[dk] = dv

    # I think authentication changes in api v3 as well, but
    # this at least let me grab an openapi.json to play with

    if args.version == '3':
        api_url=f'http://{args.server}:5240/MAAS/a/3/{ep}'
    else:
        api_url=f'http://{args.server}:5240/MAAS/api/2.0/{ep}'

    success, resp = do_request(args.X, api_url, None, datadict, args.verbose)
    if success:
        print(resp.text)
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

