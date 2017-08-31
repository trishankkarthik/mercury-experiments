#!/usr/bin/env python3


# 1st-party
import calendar
import glob
import logging
import lzma
import os
import re
import sys
import time
import traceback
import urllib.parse


SPACE_DELIMITER = ' '

# Only OK. No partial content, no redirections, no buts.
HTTP_STATUS_CODE_START = 200
HTTP_STATUS_CODE_STOP = 200
# Known HTTP methods: http://restpatterns.org/HTTP_Methods
HTTP_METHODS = {'CONNECT', 'COPY', 'DELETE', 'GET', 'HEAD', 'LOCK', 'MKCOL',
              'MOVE', 'OPTIONS', 'POST', 'PROPFIND', 'PROPPATCH', 'PUT',
              'TRACE', 'UNLOCK'}

# However, we are interested in only these.
HTTP_METHODS_FILTER = {'GET'}

LINE_REGEX = re.compile(r'^(<134>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) '
                      '(\S+) (\S+): ([0-9a-f]{64}) "(.+)" "(-)" '
                      '"([A-Z]{3,9}) (.+) (HTTP/\d\.\d) (\d{3}) (.*) '
                      '(.*) (HIT|MISS) (\d+) "(.*)" "(.*)" "(.*)"$')
SHA256_PATTERN = re.compile('^[0-9a-f]{64}$')
# URL pattern: http://stackoverflow.com/q/827557
URL_REGEX = \
    re.compile(r'^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?$')
# However, we are interested in only valid /packages/ requests.
URL_REGEX_FILTER = re.compile(r'^/packages/.+/.+/.+/.+\.\w+$')
# NOTE: For Mercury, we want to consider the cost for all types of users,
# including mirrors, bots, and even users who manually download packages with
# web browsers.
USER_AGENT_FILTER = re.compile(r'.*', flags=re.DOTALL)


class Stripper:


  def pre_walk(self, anonymized_compressed_filepath):
    self.write_counter = 0

    # Set only for filtered lines.
    self.prev_ip_address = None
    self.prev_unix_timestamp = None
    self.prev_url = None
    self.prev_user_agent = None

    anonymized_compressed_dirname = \
      os.path.dirname(anonymized_compressed_filepath)
    anonymized_compressed_filename = \
      os.path.basename(anonymized_compressed_filepath)
    prefix, date, ext = anonymized_compressed_filename.split('.')

    simple_uncompressed_filename = 'mercury.{}.log'.format(date)
    simple_uncompressed_filepath = \
      os.path.join(anonymized_compressed_dirname, simple_uncompressed_filename)

    self.simple_uncompressed_filepath = simple_uncompressed_filepath
    self.simple_uncompressed_file = open(simple_uncompressed_filepath, 'wt')


  # Write only filtered lines.
  def in_walk(self, ip_address, unix_timestamp, http_method, url,
              http_status_code, user_agent):
    if http_method in HTTP_METHODS_FILTER and \
       http_status_code >= HTTP_STATUS_CODE_START and \
       http_status_code <= HTTP_STATUS_CODE_STOP and \
       URL_REGEX_FILTER.match(url) and \
       USER_AGENT_FILTER.match(user_agent):
      # Write only filtered lines that are not consecutive duplicates.
      # That is, consider filtered lines L1 and L2 that are duplicates.
      # L2 will not be written only if it consecutively follows L1.
      if ip_address != self.prev_ip_address or \
         unix_timestamp != self.prev_unix_timestamp or \
         url != self.prev_url or \
         user_agent != self.prev_user_agent:
        # Write the new line.
        stripped_line = '"{}","{}","{}","{}"\n'.format(unix_timestamp,
                                                       ip_address, url,
                                                       user_agent)

        self.simple_uncompressed_file.write(stripped_line)
        self.write_counter += 1

        # Replace previously observed values.
        self.prev_ip_address = ip_address
        self.prev_unix_timestamp = unix_timestamp
        self.prev_url = url
        self.prev_user_agent = user_agent


  def post_walk(self, parse_error_counter, line_counter):
    write_rate = (self.write_counter / line_counter) * 100
    logging.info('Wrote {} out of {} ({}%) lines'.format(self.write_counter,
                                                         line_counter,
                                                         write_rate))

    self.simple_uncompressed_file.close()
    logging.info('W ' + self.simple_uncompressed_filepath)


class Surveyor:


  def __init__(self):
    # IP address => a set of user agents
    self.ip_address_to_user_agents = {}


  def pre_walk(self, anonymized_compressed_filepath):
    # Will be overwritten when walking the next log.
    self.anonymized_compressed_filepath = anonymized_compressed_filepath


  # Write only filtered lines.
  def in_walk(self, ip_address, unix_timestamp, http_method, url,
              http_status_code, user_agent):
    self.ip_address_to_user_agents.setdefault(ip_address,
                                              set()).add(user_agent)


  def post_walk(self, parse_error_counter, line_counter):
    number_of_users = sum(
      len(user_agents)  \
      for user_agents   \
      in self.ip_address_to_user_agents.values()
    )

    logging.info('R {}'.format(self.anonymized_compressed_filepath))
    logging.info('There were {:,} IP addresses.'\
                 .format(len(self.ip_address_to_user_agents)))
    logging.info('There were {:,} users identified by '\
                 '(IP address, user agent).'.format(number_of_users))
    logging.info('There were {:,} HTTP requests.'.format(line_counter))


def walk(anonymized_compressed_filepath, pre_walk, in_walk, post_walk):
  anonymized_compressed_filename = \
    os.path.basename(anonymized_compressed_filepath)
  prefix, date, ext = anonymized_compressed_filename.split('.')
  assert prefix == 'anonymized'
  assert ext == 'xz'

  line_counter = 0
  parse_error_counter = 0

  pre_walk(anonymized_compressed_filepath)

  # For some reason, reading the file line by line as 'b' instead of 't' is
  # more robust.
  with lzma.open(anonymized_compressed_filepath, 'rb') as \
                                                    anonymized_compressed_file:

    for line in anonymized_compressed_file:
      line_counter += 1

      try:
        # TODO: salvage as much as possible from the line
        normalized_line = line.decode('utf-8')
        tokens = LINE_REGEX.match(normalized_line).groups()

        ip_address = tokens[3]
        assert SHA256_PATTERN.match(ip_address), ip_address

        timestamp_string = tokens[4]
        # http://stackoverflow.com/a/466366
        gm_timestamp = time.strptime(timestamp_string,
                                     '%a, %d %b %Y %H:%M:%S %Z')
        unix_timestamp = calendar.timegm(gm_timestamp)

        http_method = tokens[6]
        assert http_method in HTTP_METHODS, http_method
        # Why replace quotes with nothing?
        # Because sometimes URLs with spaces are not properly quoted.
        # e.g. '"GET /packages/source/Z/Zachs-data-dump/Zachs" data dump-1.0.1.tar.gz'
        # Why unquote and then quote the URL?
        # Because we do not want to quote already quoted characters.
        url = \
          urllib.parse.quote(urllib.parse.unquote(tokens[7].replace('"', '')))
        assert URL_REGEX.match(url), url
        http_status_code = int(tokens[9])

        user_agent = tokens[16].strip()

      except:
        parse_error_counter += 1
        logging.info('WARNING: line {} was skipped!'.format(line_counter))
        logging.info(line)
        logging.info(traceback.format_exc())

      else:
        in_walk(ip_address, unix_timestamp, http_method, url, http_status_code,
                user_agent)

  parse_error_rate = (parse_error_counter / line_counter) * 100
  logging.info('Parsing error rate: {}%'.format(parse_error_rate))

  post_walk(parse_error_counter, line_counter)


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  logging.basicConfig(filename='/var/experiments-output/mercury-log-stripper.log',
                      level=logging.DEBUG, filemode='a',
                      format='[%(asctime)s UTC] [%(name)s] [%(levelname)s] '\
                             '[%(funcName)s:%(lineno)s@%(filename)s] '\
                             '%(message)s')

  if len(sys.argv) >= 2:
    pypi_log_files = sys.argv[1:]

  else:
    pypi_log_files = \
      glob.glob('/var/experiments-output/anonymized/anonymized.*.xz')

  # A surveyor for all raw logs.
  surveyor = Surveyor()

  for anonymized_compressed_filepath in pypi_log_files:
    walk(anonymized_compressed_filepath, surveyor.pre_walk, surveyor.in_walk,
         surveyor.post_walk)

    # A stripper for every raw log.
    stripper = Stripper()
    walk(anonymized_compressed_filepath, stripper.pre_walk, stripper.in_walk,
         stripper.post_walk)
