#!/home/dmick/v/bin/python3
import argparse
import os
import jenkins
import requests
import sys
import time

jenkins_user=os.environ.get('JENKINS_USER')
jenkins_token=os.environ.get('JENKINS_TOKEN')
j=jenkins.Jenkins('https://jenkins.ceph.com', jenkins_user, jenkins_token)

def main():
    print("getting nodelist...", end='', file=sys.stderr)
    nodes = j.get_nodes()
    print(f'{len(nodes)} nodes found', file=sys.stderr)

    nodetojob = dict()
    print("getting active builds...", end='', file=sys.stderr, flush=True)
    for node in nodes:
        print(".", end='', file=sys.stderr, flush=True)
        name=node['name']
        if 'Built' in name:
            name='(master)'
        nodeinfo = j.get_node_info(name)
        nodetojob[name] = dict()
        nodetojob[name]['tags'] = \
            [t['name'] for t in nodeinfo['assignedLabels'] if '+' not in t['name']]
        # node_info(depth=2) is too expensive.  Get just the running jobs.

        req = f'https://jenkins.ceph.com/computer/{name}/api/json?tree=executors[currentExecutable[url],busyExecutors,idleExecutors]'
        start = time.time()
        resp = requests.get(req)
        end = time.time()

        resp.raise_for_status()
        builds=resp.json()
        for b in builds['executors']:
            ce = b['currentExecutable']
            if not ce:
                continue
            if not 'builds' in nodetojob[name]:
                nodetojob[name]['builds'] = list()
            nodetojob[name]['builds'].append(ce['url'])
    print(file=sys.stderr)
    idlecnt = busycnt = 0
    for k,v in nodetojob.items():
        name = k
        # chop off IP addr
        name = name[name.find('+')+1:]
        if 'builds' in v:
            buildstr = f'{len(v["builds"])} active builds'
            busycnt += 1
        else:
            buildstr = 'idle'
            idlecnt += 1
        print(f'{name}: {buildstr} ({",".join(v["tags"])})')
        if 'builds' in v:
            for b in v['builds']:
                print(f'{b}')
        print()
    print(f'Idle: {idlecnt}  Busy: {busycnt}')

if __name__ == '__main__':
    sys.exit(main())
