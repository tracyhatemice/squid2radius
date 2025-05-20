#!/usr/bin/python

import sys
import argparse
import datetime
import time
import re
from subprocess import call
from collections import defaultdict
import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary

try:
    from hurry.filesize import size
except ImportError:
    print("WARNING: Unable to import hurry.filesize.  Data transfer will be " \
          "displayed in bytes.  To fix this, run `pip3 install hurry.filesize`.")

parser = argparse.ArgumentParser(description='Analyze squid log by user ' \
                                             'and upload result to RADIUS ' \
                                             'server.')
parser.add_argument('--version', action='version', version='%(prog)s 2.0')
parser.add_argument('--logfile_path', help='logfile to analyze', default='/var/log/squid/access.log')
parser.add_argument('radius_server')
parser.add_argument('radius_secret')
parser.add_argument('--seek_time', help='time to seek in the log file, ' \
                                                'in minutes. Defaults to 60 minutes',
                                                default='60', type=int)
parser.add_argument('-p', '--radius-acct-port', default='1813')
parser.add_argument('--radius-nasid', default='squid')
parser.add_argument('--squid-path', default='/usr/sbin/squid')
parser.add_argument('--exclude-pattern', help='do not send to server if ' \
                                              'username contains this regexp',
                                         default='')
parser.add_argument('--dry-run', help='run locally only and never contact the' \
                                      'server',
                                 action='store_true')
parser.add_argument('--rotation', help='rotate squid log files',
                                     action='store_true')
args = parser.parse_args()

logfile = open(args.logfile_path)
# print(logfile)

sys.stdout.write("Analyzing.")
sum_bytes = defaultdict(lambda: defaultdict(int))

for i, line in enumerate(logfile):
    if i % 10000 == 0: sys.stdout.write('.'); sys.stdout.flush()
  
    # http://wiki.squid-cache.org/Features/LogFormat
    log_time, _, log_ip, code_status, num_bytes, _, _, rfc931, _, _ = line.split()[:10]

    if abs(datetime.datetime.now() - datetime.timedelta(minutes=args.seek_time) - datetime.datetime.fromtimestamp(float(log_time)) ) > datetime.timedelta(minutes=args.seek_time): continue
    
    # unauthorized user
    if rfc931 == '-': continue

    # wrong username and/or password
    if code_status.split('/')[1] == '407': continue
    
    try:
        sum_bytes[rfc931][log_ip] += int(num_bytes)
    except KeyError:
        sum_bytes[rfc931][log_ip] = int(num_bytes)

print()
print("Sending..." if not args.dry_run else "Dry run...") 

srv = Client(server=args.radius_server, secret=args.radius_secret.encode('ascii'),
             dict=Dictionary(sys.path[0] + "/dictionary"))

if args.exclude_pattern:
    print("Exclusion check has been enabled.")
    exclude_pattern = re.compile(args.exclude_pattern)

failed_usernames = []
for username, total_bytes in sum_bytes.items():

    sys.stdout.write('\t' + username + '\n')

    for ip, bytes_per_ip in total_bytes.items():
        sys.stdout.write('\t\t' + ip + '\t')
        try:
            sys.stdout.write(size(bytes_per_ip))
        except NameError:
            sys.stdout.write(str(bytes_per_ip))

        if args.dry_run:
            sys.stdout.write("\n")
            continue

        if args.exclude_pattern and exclude_pattern.search(username):
            sys.stdout.write("...skipped!\n")
            sys.stdout.flush()
            continue

        session_id = str(time.time())

        try:
            sys.stdout.write('.')
            sys.stdout.flush()

            req = srv.CreateAcctPacket()
            req['User-Name'] = username
            req['NAS-Identifier'] = args.radius_nasid
            req['Acct-Session-Id'] = session_id
            req['Acct-Status-Type'] = 1  # Start
            req['Calling-Station-Id'] = ip
            req['Connect-Info'] = "Squid"

            reply = srv.SendPacket(req)
            if not reply.code == pyrad.packet.AccountingResponse:
                raise Exception("Unexpected response from RADIUS server")

            sys.stdout.write('.')
            sys.stdout.flush()

            req = srv.CreateAcctPacket()
            req['User-Name'] = username
            req['NAS-Identifier'] = args.radius_nasid
            req['Acct-Session-Id'] = session_id
            req['Acct-Status-Type'] = 2  # Stop
            req['Acct-Output-Octets'] = bytes_per_ip
            req['Calling-Station-Id'] = ip

            reply = srv.SendPacket(req)
            if not reply.code == pyrad.packet.AccountingResponse:
                raise Exception("Unexpected response from RADIUS server")

            sys.stdout.write('.')
            sys.stdout.flush()
        
        except Exception as e:
            failed_usernames.append((username, e))
            sys.stdout.write("FAILED!\n")
            sys.stdout.flush()
            continue

        sys.stdout.write("\n")

    sys.stdout.write("\t---------------------------\n")

if args.rotation:
    print("\nRotating squid log...")
    call([args.squid_path, "-k", "rotate"])


if failed_usernames:
  raise Exception("Unable to send stats for the following user(s):\n  "
                  + "\n  ".join(fu[0] 
                                + ' (' + fu[1].__class__.__name__ + ': '
                                + str(fu[1]) + ')'
                                for fu in failed_usernames))
