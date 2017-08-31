#!/usr/bin/env python3

'''
NOTES
=====

* There are gaps in serial IDs. Does PyPI lose some events?

* changelog action journal entries
  * 'add {role_name} {user_name}'
  * 'add {pyversion} file {filename}'
  * 'add url '
  * 'create'
  * 'docupdate'
  * 'new release'
  * 'remove'
  * 'remove file {filename}'
  * 'rename from {old}'
  * 'remove url '
  * 'remove {role_name} {user_name}'
  * 'update hosting_mode'
  * 'update xxx'

* pypi.store.Store
  * add_description_url
    * changelog: 'add url {url}'
    * actions: urls
  * add_file: Add to the database and store content to disk.
    * changelog: 'add {pyversion} file {filename}'
    * actions: file_upload
  * add_role: Add a role to the user for the package.
    * changelog: 'add {role_name} {user_name}'
    * actions: role
  * delete_role: Delete a role to the user for the package.
    * changelog: 'remove {role_name} {user_name}'
    * actions: role
  * log_docs: update https://pythonhosted.org/project/
    * changelog: 'docupdate'
    * actions: doc_upload
  * remove_description_url
    * changelog: 'remove url {url}'
    * actions: urls
  * remove_file
    * changelog: 'remove file {filename}'
    * actions: files
  * remove_package: Delete an entire package from the database.
    * changelog: 'remove'
    * actions: remove_pkg
  * remove_release: Delete a single release from the database.
    * changelog: 'remove'
    * actions: remove_pkg
  * rename_package: Rename a package.
    * changelog: 'rename from {old}'
    * actions: None
  * set_package_hosting_mode
    * changelog: 'update hosting_mode'
    * actions: urls
  * store_package
    * changelog: 'create', 'new release', 'update xxx'
    * actions: submit, submit_pkg_info, pkg_edit, file_upload

* pypi.webui.WebUI actions
  * actions we DO see in changelog
    * doc_upload
    * file_upload
    * files: List files and handle file submissions.
    * pkg_edit: Edit info about a bunch of packages at one go
    * remove_pkg: Remove a release or a whole package from the db. Only
      owner may remove an entire package - Maintainers may remove releases.
    * role: Add a Role to a user.
    * submit: Handle the submission of distro metadata.
    * submit_pkg_info: Handle the submission of distro metadata as a PKG-INFO
      file.
    * urls: List urls and handle changes.

  * actions we DO NOT see in changelog
    * ['about', 'addkey', 'browse', 'claim', 'clear_auth', 'delete_user',
      'delkey', 'display', 'display_pkginfo', 'doap', 'dropid', 'exception',
      'forgotten_password', 'forgotten_password_form', 'gae_file', 'home',
      'index', 'json', 'lasthour', 'list_classifiers', 'login', 'logout',
      'openid', 'openid_decide_post', 'openid_endpoint', 'openid_return',
      'packages_rss', 'password_reset', 'pw_reset', 'pw_reset_change',
      'register_form', 'role_form', 'rss', 'rss_regen', 'search', 'show_md5',
      'submit_form', 'user', 'user_form', 'verify']

* To understand all actions, look at:
  * https://bitbucket.org/pypa/pypi/src/60c336a587ab4ba97c758f35bf1c3cc716a18029/webui.py?at=default#cl-678
  * anything that calls Store.add_journal_entry in https://bitbucket.org/pypa/pypi/src/60c336a587ab4ba97c758f35bf1c3cc716a18029/store.py?at=default

TODO
====
* how often are project metadata updated?


REFERENCES
==========

* http://bpaste.net/show/tcKzuL7F5aDz1WSyRwbm/
* https://wiki.python.org/moin/PyPIXmlRpc
* https://bitbucket.org/pypa/pypi/
* http://python-packaging-user-guide.readthedocs.org/en/latest/glossary.html
'''


################################### IMPORTS ###################################


# 1st-party
import argparse
import calendar
import collections
import datetime
import operator
import os
import re
import time
import xmlrpc.client


################################### GLOBALS ###################################


CHANGELOG_FILENAME = '/var/experiments-output/{since}-{until}.changelog'
DELIMITER = ';'
PYPI_SERVICE = 'https://pypi.python.org/pypi'
SERIAL_INDEX = 4
SERIAL_SENTINEL = -1
TIMESTAMP_INDEX = 2


################################## FUNCTIONS ##################################


def unix_timestamp(year=None, month=None, day=None):
  '''
  return:
    if year or month or day is given:
      POSIX timestamp of year/month/day at midnight in UTC.
    else:
      POSIX timestamp of current time in UTC.
  '''

  if not (year or month or day):
    utc_time_tuple = time.gmtime()

  else:
    utc_time_tuple = \
      datetime.datetime(year=year, month=month, day=day).utctimetuple()

  return calendar.timegm(utc_time_tuple)


################################### CLASSES ###################################


class Change:
  def __init__(self, name):
    self.name = name


  def __repr__(self):
    return '{}({})'.format(self.__class__.__name__, self.name)


class AddPackage(Change): pass


class AddProject(Change): pass


class RemovePackage(Change): pass


class RemoveProject(Change): pass


class ChangeLogReader(object):
  def __init__(self, since=unix_timestamp(2014, 3, 21),
                     until=unix_timestamp(2014, 4, 20)):
    assert since < until

    self.since = since
    self.until = until

    self.add_file_events = 0
    self.add_role_events = 0
    self.creation_events = 0
    self.default_events = 0
    self.delete_role_events = 0
    self.remove_file_events = 0
    self.remove_release_events = 0
    self.remove_package_events = 0

    # ordered by serial ID or timestamp
    # [(Change(name), creation_timestamp), ...]
    self.changes = []

    # Specific regex MUST ALWAYS PRECEDE general regex!
    self.action_regex_handlers = (
      ('^add (.+) file (.+)$', 'handle_add_file'),
      ('^add (.+) (.+)$', 'handle_add_role'),
      ('^create$', 'handle_create'),
      ('^remove$', 'handle_remove'),
      ('^remove file (.+)$', 'handle_remove_file'),
      ('^remove (.+) (.+)$', 'handle_delete_role')
    )


  def aggregate(self):
    # int (timestamp > 0): [Change(name), ...]
    changes_by_timestamp = collections.OrderedDict()
    prev_timestamp = 0

    # Since self.changes is ordered by serial, each append will be ordered by
    # serial too.
    for change, curr_timestamp in self.changes:
      assert prev_timestamp <= curr_timestamp
      changes_by_serial = changes_by_timestamp.setdefault(curr_timestamp, [])
      changes_by_serial.append(change)
      prev_timestamp = curr_timestamp

    return changes_by_timestamp


  def filter_changes(self, since=None, until=None):
    since = since or self.since
    until = until or self.until

    return [(change, timestamp) for change, timestamp in self.changes \
                                if since <= timestamp and timestamp < until]


  def handle_add_file(self, change, action_match):
    name, version, timestamp, action, serial = change
    pyversion, filename = action_match.groups()

    self.add_file_events += 1
    self.changes.append((AddPackage('{}/{}/{}/{}'.format(pyversion,
                                                         name[0], name,
                                                         filename)),
                        timestamp))


  def handle_add_role(self, change, action_match):
    self.add_role_events += 1


  def handle_change(self, change):
    name, version, timestamp, action, serial = change

    for regex, handle_action in self.action_regex_handlers:
      action_match = re.match(regex, action)
      if action_match:
        handle_action = getattr(self, handle_action)
        handle_action(change, action_match)
        break

    # If the action did not match anything of interest, call a default handler.
    else:
      self.handle_default(change, action_match)


  def handle_create(self, change, action_match):
    name, version, timestamp, action, serial = change

    self.creation_events += 1
    self.changes.append((AddProject(name), timestamp))


  # Default action handler for unmatched actions.
  def handle_default(self, change, action_match):
    self.default_events += 1


  def handle_delete_role(self, change, action_match):
    self.delete_role_events += 1


  def handle_remove(self, change, action_match):
    name, version, timestamp, action, serial = change

    if version == 'None':
      self.remove_package_events += 1
      self.changes.append((RemoveProject(name), timestamp))
    else:
      # The change log does not tell us what pyversion it is,
      # so we glob for everything.
      pyversion = '*'
      # Again, the change log does not tell us what file name exactly,
      # so we glob for everything.
      filename = '{}-{}.*'.format(name, version)

      self.remove_release_events += 1
      self.changes.append((RemovePackage('{}/{}/{}/{}'.format(pyversion,
                                                              name[0], name,
                                                              filename)),
                           timestamp))


  def handle_remove_file(self, change, action_match):
    name, version, timestamp, action, serial = change
    filename = action_match.group(1)
    # The change log does not tell us what pyversion it is,
    # so we glob for everything.
    pyversion = '*'

    self.remove_file_events += 1
    self.changes.append((RemovePackage('{}/{}/{}/{}'.format(pyversion,
                                                            name[0], name,
                                                            filename)),
                         timestamp))


  def parse_changelog(self):
    changelog_filename = CHANGELOG_FILENAME.format(since=self.since,
                                                   until=self.until)

    with open(changelog_filename, 'rt') as changelog_file:
      prev_serial = -1

      for line in changelog_file:
        name, version, timestamp, action, curr_serial = line.split(DELIMITER)
        # Cast data to expected types to remove element of surprise.
        timestamp, curr_serial = int(timestamp), int(curr_serial)
        assert prev_serial < curr_serial
        yield name, version, timestamp, action, curr_serial
        prev_serial = curr_serial


  def read(self):
    for change in self.parse_changelog():
      self.handle_change(change)


  def summarize(self):
    '''Documents how PyPI changelog events, in their glossary, translates to
    our glossary.'''

    since_datetime = datetime.datetime.utcfromtimestamp(self.since)
    until_datetime = datetime.datetime.utcfromtimestamp(self.until)
    seconds_elapsed = self.until - self.since
    print('# of seconds since {} until {}: {}s'.format(since_datetime,
                                                       until_datetime,
                                                       seconds_elapsed))
    print()

    project_creation_rate = self.creation_events / seconds_elapsed
    print('# of created projects: {}'.format(self.creation_events))
    print('Rate: {}/s'.format(project_creation_rate))
    print()

    project_deletion_rate = self.remove_package_events / seconds_elapsed
    print('# of deleted projects: {}'.format(self.remove_package_events))
    print('Rate: {}/s'.format(project_deletion_rate))
    print()

    project_growth = self.creation_events - self.remove_package_events
    project_growth_rate = project_growth / seconds_elapsed
    print('Net # of created projects: {}'.format(project_growth))
    print('Rate: {}/s'.format(project_growth_rate))
    print()

    role_addition_rate = self.add_role_events / seconds_elapsed
    print('# of times some developer was added to a project: {}'.\
          format(self.add_role_events))
    print('Rate: {}/s'.format(role_addition_rate))
    print()

    role_deletion_rate = self.delete_role_events / seconds_elapsed
    print('# of times some developer was removed from a project: {}'.\
          format(self.delete_role_events))
    print('Rate: {}/s'.format(role_deletion_rate))
    print()

    role_growth = self.add_role_events - self.delete_role_events
    role_growth_rate = role_growth / seconds_elapsed
    print('Net # of times some developer was added to a project: {}'.\
          format(role_growth))
    print('Rate: {}/s'.format(role_growth_rate))
    print()

    file_addition_rate = self.add_file_events / seconds_elapsed
    print('# of added packages: {}'.format(self.add_file_events))
    print('Rate: {}/s'.format(file_addition_rate))
    print()

    release_deletion_rate = self.remove_release_events / seconds_elapsed
    print('# of times ALL packages (of some project) at some version '\
          'were deleted: {}'.format(self.remove_release_events))
    print('Rate: {}/s'.format(release_deletion_rate))
    print()

    file_deletion_rate = self.remove_file_events / seconds_elapsed
    print('# of times SOME package (of some project) at some version '\
          'was deleted: {}'.format(self.remove_file_events))
    print('Rate: {}/s'.format(file_deletion_rate))
    print()

    default_event_rate = self.default_events / seconds_elapsed
    print('# of other actions: {}'.format(self.default_events))
    print('Rate: {}/s'.format(default_event_rate))


class ChangeLogWriter:
  def __init__(self, since, until):
    '''
    parameters:
      since:
        UTC integer seconds when the changelog begins.
      until:
        UTC integer seconds when the changelog ends.
    '''

    self.since = since
    self.until = until
    self.server = xmlrpc.client.Server(PYPI_SERVICE)


  def __changelog(self, with_ids=True):
    '''
    parameters:
      with_ids:
        if with_ids:
          changelog is sorted by PyPI event serial IDs.
        else:
          changelog is sorted by PyPI event POSIX timestamps.

    return:
      if with_ids:
        return [(name, version, timestamp, action, serial), ...]
      else:
        return [(name, version, timestamp, action, SERIAL_SENTINEL), ...]

      All timestamps are UTC values.
    '''

    changes = self.server.changelog(self.since, with_ids)

    if with_ids:
      sort_key_index = SERIAL_INDEX
      previous_serial = SERIAL_SENTINEL
      missing_serials = set()
    else:
      sort_key_index = TIMESTAMP_INDEX
      previous_timestamp = 0

    # NOTE: Experience is that changelog is NOT ordered!
    changes = sorted(changes, key=operator.itemgetter(sort_key_index))
    # filter changelog such that all events are less than the until timestamp
    changes = [change for change in changes \
              if change[TIMESTAMP_INDEX] < self.until]

    # Run sanity checks, and normalize changelog.
    for change in changes:
      name, version, timestamp, action = change[:SERIAL_INDEX]
      assert timestamp < self.until

      if with_ids:
        serial = change[SERIAL_INDEX]
        assert previous_serial < serial
        assert serial not in missing_serials

        if previous_serial > SERIAL_SENTINEL and \
           (serial - previous_serial) > 1:
          missing_serials |= set(range(previous_serial + 1, serial))

        previous_serial = serial

      else:
        assert previous_timestamp <= timestamp
        previous_timestamp = timestamp
        # normalize changelog to always consist of 5-tuples with the serial
        change.append(SERIAL_SENTINEL)

    return changes


  def write(self):
    changelog_filename = CHANGELOG_FILENAME.format(since=self.since,
                                                   until=self.until)

    with open(changelog_filename, 'wt') as changelog_file:
      for name, version, timestamp, action, serial in self.__changelog():
        assert DELIMITER not in name
        if version:
          assert DELIMITER not in version
          # Yes, there can be whitespace sometimes left in versions.
          version = version.strip()
        assert DELIMITER not in action

        line = '{name}{delimiter}' \
               '{version}{delimiter}' \
               '{timestamp}{delimiter}' \
               '{action}{delimiter}' \
               '{serial}\n'.format(delimiter=DELIMITER, name=name,
                                   version=version, timestamp=timestamp,
                                   action=action, serial=serial)
        changelog_file.write(line)


#################################### MAIN #####################################


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  parser = argparse.ArgumentParser(prog='PROG')
  parser.add_argument('-r', '--read', default=True, action='store_true',
                      help='Read a written changelog from PyPI')
  parser.add_argument('-w', '--write', default=False, action='store_true',
                      help='Write a changelog from PyPI')
  args = parser.parse_args()

  year, month, day = 2014, 3, 21
  since = unix_timestamp(year=year, month=month, day=day)
  until = unix_timestamp(year=year, month=month+1, day=day-1)

  if args.write:
    changelog_writer = ChangeLogWriter(since, until)
    changelog_writer.write()

  if args.read:
    changelog_reader = ChangeLogReader(since, until)
    changelog_reader.read()
    changelog_reader.summarize()


