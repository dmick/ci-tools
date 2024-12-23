#!/home/dmick/v/bin/python3 
import argparse
import datetime
fromtimestamp=datetime.datetime.fromtimestamp
import jenkins
import json
import os
import re
import sys
import time

# set JENKINS_USER and JENKINS_TOKEN in environment

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", "--json", action='store_true', help="Output json")
    ap.add_argument("-P", "--allparams", action='store_true', help="Output all job parameters")
    ap.add_argument("-l", "--list", action='store_true', help="List all jobs and exit")
    ap.add_argument("-c", "--count", type=int, help="Limit output to this many jobs")
    ap.add_argument('jobre', type=str, nargs="?", default='^ceph-dev-new$', help="regexp to match job name")
    return ap.parse_args() 


def to_minsec(ms):
    return sec_to_minsec(ms // 1000)


def sec_to_minsec(totalsec):
    h = totalsec // 3600
    m = (totalsec - (h * 3600)) // 60
    s = totalsec - (h * 3600) - (m * 60)
    return f'{h:02d}:{m:02d}:{s:02d}'


def decruft(reason):
    '''
    Remove some cruft from lines like:
    GitHub pull request #54725 of commit 75e88727ef2bfd13bfcad68c6e60db6bf9d73364, no merge conflicts.
    '''
    cruftsubs = [
        ('GitHub pull request ', 'PR'),
        ('of commit ', ''),
        (', no merge conflicts.', ''),
        ('build number ', '#'),
    ]
    for s,r in cruftsubs:
        reason = re.sub(s, r, reason)
    return reason


def output(name, buildnum, reason, paramdict, start, age, bi, waittime, returndict=False):
    age = sec_to_minsec(age)
    if returndict:
        outdict = {
            "buildnum": buildnum,
            "reason": reason,
            "params": paramdict,
            "started": start,
            "building": bi["building"],
        }
        if bi["building"]:
            outdict.update(dict(
                estimatedDuration=to_minsec(bi["estimatedDuration"]),
                age=age,
            ))
        else:
            outdict.update(dict(
                buildtime=to_minsec(bi['duration']),
                result=bi['result'],
                waittime=waittime,
            ))
        return outdict

    nltab = "\n\t"
    print(f'#{buildnum}: {reason}', end='')
    if len(paramdict):
        print(f'{nltab}{nltab.join(paramdict.values())}', end='')
    print(f'{nltab}started: {start} ', end='')
    if bi['building']:
        print(f'building for {age}, est duration {to_minsec(bi["estimatedDuration"])}')
    else: 
        print(f'waited {waittime}, took {to_minsec(bi["duration"])} {bi["result"]}')


def ts_to_str(ts):
    return fromtimestamp(ts).strftime('%d %b %H:%M:%S')


def main():
    jenkins_user=os.environ.get('JENKINS_USER')
    jenkins_token=os.environ.get('JENKINS_TOKEN')
    j=jenkins.Jenkins('https://jenkins.ceph.com', jenkins_user, jenkins_token)

    args = parse_args()

    if args.list:
        ji = j.get_info()
        jobs = ji['jobs']
        for job in jobs:
            print(f'{job["name"]}')
        return 0

    # jobinfo = j.get_job_info_regex(args.jobre)
    # get_job_info_regex doesn't allow passing "fetch_all_builds", so
    # recreate it here
    joblist = j.get_all_jobs()
    jobinfo = list()
    for job in joblist:
        if re.search(args.jobre, job['name']):
            jobinfo.append(j.get_job_info(job['name'], fetch_all_builds=True))


    for ji in jobinfo:
        name=ji['name']
        if args.json:
            outdict = dict(name=name, builds=list())
        buildcount = 0
        for build in ji['builds']:
            if args.count and buildcount >= args.count:
                break
            buildcount += 1
            buildnum = build['number']
            bi = j.get_build_info(name, buildnum)
            '''
            {'_class': 'hudson.model.CauseAction',
             'causes': [{'_class': 'org.jenkinsci.plugins.ghprb.GhprbCause',
                 'shortDescription': 'GitHub pull request #56203 of commit '
                                     'ab4c5daead7f26d41028625453d50bb58d3b02be,'
                                     ' no merge conflicts.'}]}

             {'_class': 'jenkins.metrics.impl.TimeInQueueAction',
              'blockedDurationMillis': 0,
              'blockedTimeMillis': 0,
              'buildableDurationMillis': 4,
              'buildableTimeMillis': 4,
              'buildingDurationMillis': 985724,
              'executingTimeMillis': 985724,
              'executorUtilization': 1.0,
              'subTaskCount': 0,
              'waitingDurationMillis': 6797,
              'waitingTimeMillis': 6797},

            '''
            reason = "??"
            paramnames = list()
            paramdict=dict()
            for act in bi['actions']:
                cls = act.get('_class', None)
                if cls is None:
                    continue

                if cls.endswith('hudson.model.CauseAction'):
                    if len(act['causes']) > 1:
                        print(f'{name} #{buildnum} has more than one cause?', file=sys.stderr)
                    reason = act['causes'][0]['shortDescription']

                if cls.endswith('ParametersAction'):
                    params = act['parameters']
                    pois = ['BRANCH', 'ARCHS', 'DISTROS', 'FLAVOR']
                    for param in params:
                        paramnames.append(param['name'])
                        if args.allparams or param['name'] in pois:
                            paramdict[param['name']] = param['value']
                
                if cls.endswith('TimeInQueueAction'):
                    waittime = None
                    if bi['building'] == False:
                        waittime = to_minsec(act['waitingTimeMillis'])

            reason = decruft(reason)
            start = ts_to_str(bi['timestamp'] / 1000)
            age = int(int(time.time()) - (bi['timestamp'] / 1000))
            if args.json:
                outdict['builds'].append(output(name, buildnum, reason, paramdict, start, age, bi, waittime, returndict=True))
            else:
                output(name, buildnum, reason, paramdict, start, age, bi, waittime, returndict=False)
    if args.json:
        print(json.dumps(outdict))

if __name__ == "__main__":
    sys.exit(main())
