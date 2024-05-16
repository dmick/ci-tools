#!/home/dmick/v/bin/python3
import argparse
import os
import jenkins
import sys

jenkins_user=os.environ.get('JENKINS_USER')
jenkins_token=os.environ.get('JENKINS_TOKEN')
j=jenkins.Jenkins('https://jenkins.ceph.com', jenkins_user, jenkins_token)

def main():
    nodes = j.get_nodes()
    builds = j.get_running_builds()

    print(f'{len(nodes)} nodes, {len(builds)} running builds')
    nodetojob = dict()
    for node in nodes:
        name=node['name']
        nodeinfo = j.get_node_info(name)
        nodetojob[name] = dict()
        nodetojob[name]['tags'] = \
            [t['name'] for t in nodeinfo['assignedLabels'] if '+' not in t['name']]
        for b in builds:
            if b['node'] == name:
                if not 'builds' in nodetojob[name]:
                    nodetojob[name]['builds'] = list()
                nodetojob[name]['builds'].append(b)

    for k,v in nodetojob.items():
        name = k
        # chop off IP addr
        name = name[name.find('+')+1:]
        print(f'{name} ({",".join(v["tags"])}): ', end='')
        if not 'builds' in v:
            print('idle')
            continue
        for b in v['builds']:
            print(f'{b["name"]} #{b["number"]} ', end='')
        print()

if __name__ == '__main__':
    sys.exit(main())
