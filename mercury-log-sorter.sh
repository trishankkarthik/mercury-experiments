#!/bin/bash

umask 007

cd /var/experiments-output/anonymized/

for log in mercury.*.log
do
  # Sort by timestamp (k1), IP (k2), user-agent (k4), URL (k3).
  time sort --field-separator=, --unique -k1 -k2 -k4 -k3 $log > sorted.$log
  echo sorted.$log
done

rm mercury.*.log
echo 'rm mercury.*.log'

time sort --field-separator=, --unique -k1 -k2 -k4 -k3 -ms -o sorted.mercury.log sorted.mercury.*.log
echo sorted.mercury.log

rm sorted.mercury.*.log
echo 'rm sorted.mercury.*.log'

mkdir /var/experiments-output/simple/
mv sorted.mercury.log /var/experiments-output/simple/
