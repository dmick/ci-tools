#!/usr/bin/python3

import os
import sys
import subprocess
import yaml

ANSIBLE_INVENTORY = os.environ.get('ANSIBLE_INVENTORY', '/home/dmick/src/ceph/ceph-sepia-secrets/ansible/inventory')
if ANSIBLE_INVENTORY.endswith('/sepia'):
    ANSIBLE_INVENTORY=ANSIBLE_INVENTORY[:-6]

def collect_jenkins_slaves():
    jenk_proc = subprocess.run(["jenkins.tags", "-o", "-d", " ",],
                               capture_output=True, check=True)
    lines = jenk_proc.stdout.decode().split('\n')
    return sorted([l.strip() for l in lines if l])


def collect_ansible_hosts():
    ans_proc = subprocess.run(
        [
        "/home/dmick/v/bin/ansible-playbook",
        "--list-hosts",
        "--limit",
        "jenkins_builders",
        "slave.yml",
        ],
        capture_output=True,
        check=True)
    ans = list()
    collect = False
    for l in ans_proc.stdout.decode().split('\n'):
        if l.startswith('    hosts'):
            collect = True
        if not collect:
            continue
        ans.append(l.strip())
    return sorted(ans)

def collect_ansible_hosts_and_tags():
    ans = list()
    with open(ANSIBLE_INVENTORY + '/group_vars/jenkins_builders.yml') as y:
        groupvars = yaml.safe_load(y)
    for k,v in groupvars['jenkins_labels'].items():
        ans.append(f'{k} {v}')
    return sorted(ans)

def split_sort_join(s):
    return ' '.join(sorted(s.split()))


def main():
    jenk = collect_jenkins_slaves()
    '''
    smithi015 172.21.15.15+smithi015 centos7 libvirt smithi vagrant
    '''
    ans = collect_ansible_hosts_and_tags()

    for j in jenk:
        jhost, jtags = j.split(maxsplit=1)
        jhost = jhost.replace(':', '')
        for a in ans:
            ahost, atags = a.split(maxsplit=1)
            if ahost not in jhost and jhost not in ahost:
                continue
            jtags = jtags.replace(" OFFLINE", "")
            jtags = jtags.split(maxsplit=1)[1]
            atags = split_sort_join(atags)
            jtags = split_sort_join(jtags)
            
            if jtags != atags:
                print(f'{jhost}')
                print(f'jenkins tags: {jtags}')
                print(f'ansible tags: {atags}')
                print()
            break


if __name__ == "__main__":
    sys.exit(main())
