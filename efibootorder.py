#!/usr/bin/python3

#
# for the Supermicro 'trial' machines.  Should be adaptable to
# others but I haven't tried to make it very generic
#
# Using Redfish, scan the EFI boot order, and report on whether 
# the overall order includes
# 1) the first v4 PXE interface
# 2) the hard disk
# 3) the EFI shell
# int that order.  Complain if not.  If you add the --fix
# flag, attempt to rewrite it so that those devices are first,
# in that order.
# Without --fix it only reports.
#
# put ipmi ipmiuser:ipmipass in ~/.ipmicreds
#

import argparse
import json
import os
import pprint
import requests
import sys
import urllib3
from copy import copy
urllib3.disable_warnings()

# these are the strings for finding the devices from the 
# redfish output of boot order
EFISHELLSTR='EFI Shell'
HARDDISKSTR='UEFI Hard Disk'
PXESTR='F0) UEFI PXE IPv4'

ipmiuser, ipmipass = open(os.path.expanduser('~/.ipmicreds')). read().strip().split(':')

def get_bootorder(host):
    if 'ipmi' not in host:
        host = host + '.ipmi.sepia.ceph.com'
    resp = requests.get(
        url=f'https://{host}/redfish/v1/Systems/1/Oem/Supermicro/FixedBootOrder',
        verify=False,
        auth=(ipmiuser,ipmipass),
    )
    resp.raise_for_status()
    return resp.json()['FixedBootOrder']

def find_indices_by_substr(l, s):
    indices = list()

    for i, e in enumerate(l):
        if s in e:
            indices.append(i)
    return indices

def find_index_by_substr(l, s):
    indices = find_indices_by_substr(l, s)
    ni = len(indices)
    if ni == 0 or ni > 1:
        raise RuntimeError(f'found {ni} entries containing {s}')
    return indices[0]
            
def bootorder_ok(boot_order):
    diskindex = shellindex = pxeindex = -1
    shellindex = find_index_by_substr(boot_order, EFISHELLSTR)
    diskindex = find_index_by_substr(boot_order, HARDDISKSTR)
    pxeindex = find_index_by_substr(boot_order, PXESTR)

    return (pxeindex < diskindex < shellindex)
    

def fix_bootorder(host, boot_order):
    if bootorder_ok(boot_order):
        return None

    old_order = copy(boot_order)
    diskindex = shellindex = pxeindex = -1
    shellindex = find_index_by_substr(boot_order, EFISHELLSTR)
    diskindex = find_index_by_substr(boot_order, HARDDISKSTR)
    pxeindex = find_index_by_substr(boot_order, PXESTR)

    new_order = [
        old_order[pxeindex],
        old_order[diskindex],
        old_order[shellindex],
        *([
            item for index, item in enumerate(old_order)
            if index not in (pxeindex, diskindex, shellindex)
        ])
    ]
    return new_order


# curl -k -v -X PATCH -d '{"FixedBootOrder": ["UEFI Network:(B1/D0/F0) UEFI PXE IPv4: Intel(R) Ethernet Controller E810-XXV for SFP(MAC:905A08776332)","UEFI CD/DVD","UEFI USB Hard Disk", "UEFI USB CD/DVD","UEFI USB Key","UEFI USB Floppy","UEFI USB Lan", "UEFI AP:UEFI: Built-in EFI Shell", "UEFI Hard Disk:ubuntu"]}' 'https://trial198.ipmi/redfish/v1/Systems/1/Oem/Supermicro/FixedBootOrder'

def write_bootorder(host, bootorder):
    if 'ipmi' not in host:
        host = host + '.ipmi.sepia.ceph.com'
    resp = requests.patch(
        verify=False,
        auth=(ipmiuser,ipmipass),
        headers={"Content-Type": "application/json"},
        url=f'https://{host}/redfish/v1/Systems/1/Oem/Supermicro/FixedBootOrder',
        data=json.dumps({"FixedBootOrder": bootorder}),
    )
    resp.raise_for_status()

    # $ curl -k -v -X POST -d '{"ResetType": "GracefulRestart"}' 'https://trial198.ipmi/redfish/v1/Systems/1/Actions/ComputerSystem.Reset'
    resp = requests.post(
        verify=False,
        auth=(ipmiuser,ipmipass),
        headers={"Content-Type": "application/json"},
        url=f'https://{host}/redfish/v1/Systems/1/Actions/ComputerSystem.Reset',
        data='{"ResetType":"GracefulRestart"}',
    )
        
    resp.raise_for_status()


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--fix', action='store_true', help='swap shell and disk if out of order (default is to warn only)')
    ap.add_argument('host', nargs='*', help='host')
    return ap.parse_args()


def main():
    args = parse_args()
    hostnames = args.host
    for hostname in hostnames:
        bootorder = get_bootorder(hostname)

        if bootorder_ok(bootorder):
            print(f'{hostname} ok')
            continue

        new_order = fix_bootorder(hostname, bootorder)
        print(hostname)
        for o, n in zip(bootorder, new_order):
            if o != n:
                print(f'{o} ===> {n}')
            else:
                print(f'{o}')
        if args.fix:
            write_bootorder(hostname, new_order)
            validate_bootorder = get_bootorder(hostname)
            if new_order != validate_bootorder:
                raise RuntimeError(f'{hostname} boot order did not change')


if __name__ == "__main__":
    sys.exit(main())
