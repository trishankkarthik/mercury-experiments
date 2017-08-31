#!/usr/bin/env python3

import csv
import os

SINCE_TIMESTAMP = 1395359999

os.chdir('/var/experiments-output/simple/')

with open('sorted.mercury.log', 'rt') as first_requests_file, \
     open('sorted.mercury.log.new', 'wt') as second_requests_file:

    visited_ips = set()

    for first_request in first_requests_file:
        ts, ip, url, ua = first_request.split(',', 3)
        ts = ts.strip('"').strip()
        ip = ip.strip('"').strip()
        url = url.strip('"').strip()
        # NOTE: Some *#$@#! user agent strings have " in them!
        ua = ua.replace('"', '').strip()

        if ip not in visited_ips:
            second_request = '"{}","{}","{}","{}"\n'.format(ts, ip, url, ua)
            second_requests_file.write(second_request)
            visited_ips.add(ip)

# test that we can use CSV to read the file
with open('sorted.mercury.log.new', 'rt') as second_requests_file:
    second_requests = csv.reader(second_requests_file)
    count = 0

    for ts, ip, url, ua in second_requests:
        count += 1

    print('Successfully wrote and read {:,} lines.'.format(count))
