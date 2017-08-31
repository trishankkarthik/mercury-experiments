#!/bin/sh

# This is a script to automate the filtration of logs so that we do is
# reproducible and can be checked for errors.

EXPERIMENTS_DIR=/var/experiments

# Keep only successful HTTP requests for /packages/.* from ALL UAs.
time ./mercury-log-stripper.py

# Sort these requests by time and merge them all.
time ./mercury-log-sorter.sh

# Make a copy of these requests, but limited to the first day.
time ./trim-sorted-mercury-log.py

# Go to where the log was merged.
cd /var/experiments-output/simple/

# List number of lines.
time wc -l sorted.mercury.log*
