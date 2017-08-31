'''
A module featuring common classes and functions to be reused by utilities that
write, for example, TUF or Mercury metadata.
'''


# 1st-party
import binascii
import datetime
import errno
import hashlib
import json
import logging
import os
import shutil


# 2nd-party
from changelog import ChangeLogReader, unix_timestamp
from nouns import LOG_FORMAT


class MetadataWriter:


  '''
  A base class for writing metadata.
  '''


  def __init__(self, repository, metadata_directory, delete=True):
    logging.debug('Init...')

    self.repository = repository

    # 755 for directories, 644 for files
    os.umask(0o022)

    if delete:
      self.rmdir(metadata_directory)
    self.mkdir(metadata_directory)
    self.metadata_directory = metadata_directory

    self.reset_metadata()

    logging.debug('...done.')


  # Expires this many days from this UTC timestamp.
  # Use the Javascript ISO 8601 format.
  def __make_expiration_timestamp(self, timestamp, days):
    expires = datetime.datetime.utcfromtimestamp(timestamp)+\
              datetime.timedelta(days=days)
    return expires.isoformat()+'Z'


  # Deterministic generation of "signature" given the same filenames, timestamp,
  # and version number.
  # EITHER the filenames, timestamp, OR the version number MUST change in order
  # for the entire signature to change.
  def __make_pseudo_signature(self, filenames, timestamp, version):
    change = '{}{}{}'.format(''.join(sorted(filenames)), timestamp, version)
    # Concatenate two 64-byte hashes to get one 128-byte "signature".
    first_half = self.get_sha256(change.encode('utf-8'))
    second_half = self.get_sha256(first_half.encode('utf-8'))
    return first_half+second_half


  def flush_metadata(self, timestamp):
    assert timestamp > 0

    # projects subordinates
    #for projects_subordinate in self.repository.projects_subordinates:
    #  filename = 'packages/{}.json'.format(projects_subordinate)
    #  metadata_version = \
    #   self.repository.get_projects_subordinate_version(projects_subordinate)
    #  metadata_json = \
    #            self.projects_subordinates_metadata_json[projects_subordinate]
    #  self.write_json_to_disk(filename, metadata_version, metadata_json)

    if len(self.repository.projects.dirty) > 0:
      # Write only dirty projects (i.e. with dirty metadata).
      for project_name in self.repository.projects.dirty:
        filename = 'packages/{}.json'.format(project_name)
        # NOTE: Up to subclass to decide how to identifity a project metadata
        # file: e.g. django.version.json or django.hash.version instead of
        # django.json.
        metadata_identifier = self.project_metadata_identifier(project_name)
        metadata_json = self.project_developer_metadata_json[project_name]
        self.write_json_to_disk(filename, metadata_identifier, metadata_json)
        self.repository.projects.unmark_project_as_dirty(project_name)

      # projects administrator
      #self.write_json_to_disk('packages.json',
      #                        self.repository.projects_administrator_version,
      #                        self.projects_administrator_metadata_json)

      # snapshot administrator
      # NOTE: We identify every snapshot metadata file with the "current"
      # timestamp, and not the version number of the snapshot metadata file.
      self.write_json_to_disk('snapshot.json',
                              timestamp,
                              self.snapshot_administrator_metadata_json)

    else:
      logging.debug('No dirty metadata to flush to disk.')


  @classmethod
  def get_random_keyid(cls):
    return cls.get_random_hexstring(64)


  @classmethod
  def get_random_ed25519_keyval(cls):
    return cls.get_random_hexstring(64)


  @staticmethod
  def get_random_hexstring(length_in_hex):
    assert length_in_hex % 2 == 0
    return binascii.b2a_hex(os.urandom(int(length_in_hex/2))).decode('utf-8')


  @staticmethod
  def get_sha256(data):
    return hashlib.sha256(data).hexdigest()


  @staticmethod
  def get_target_metadata(sha256, length):
    assert length >= 0

    return {
      'hashes': {
        'sha256': sha256
      },
      'length': length
    }


  def jsonify(self, metadata, debug=True):
    # the root json data type
    assert isinstance(metadata, dict)

    if debug:
      indent = 1
      separators = (', ', ': ')
      sort_keys = True
    else:
      indent = None
      separators = (',', ':')
      sort_keys = False

    return json.dumps(metadata, indent=indent, separators=separators,
                      sort_keys=sort_keys).encode('utf-8')


  def make_project_developer_metadata(self, timestamp):
    # Update only dirty projects (i.e. with dirty metadata).
    for project_name in self.repository.projects.dirty:
      keyids = self.repository.projects.get_keyids_for_project(project_name)
      targets = \
        self.repository.projects.get_targets_metadata_for_project(project_name)
      version = self.repository.projects.get_project_version(project_name)

      self.project_developer_metadata[project_name] = \
                                self.make_targets_metadata(keyids=keyids,
                                                           targets=targets,
                                                           timestamp=timestamp,
                                                           version=version)
      self.project_developer_metadata_json[project_name] = \
                    self.jsonify(self.project_developer_metadata[project_name])


  def make_projects_administrator_metadata(self):
    '''Write to:
      1. self.projects_administrator_metadata
      2. self.projects_administrator_metadata_json'''

    keyids = self.repository.projects_administrator_keyids
    keyid_to_keyval = self.repository.keyid_to_keyval

    roles = self.repository.projects_subordinates
    role_to_keyids = self.repository.projects_subordinates_to_keyids
    role_to_paths = {role: ['packages/*/{}/*'.format(role)] for role in roles}

    version = self.repository.projects_administrator_version

    self.projects_administrator_metadata = \
      self.make_targets_metadata(keyids=keyids,
                                 keyid_to_keyval=keyid_to_keyval, roles=roles,
                                 role_to_keyids=role_to_keyids,
                                 role_to_paths=role_to_paths, version=version)

    self.projects_administrator_metadata_json = \
                            self.jsonify(self.projects_administrator_metadata)


  def make_projects_subordinates_metadata(self):
    '''Write to:
      1. self.projects_subordinates_metadata
      2. self.projects_subordinates_metadata_json'''

    keyids = self.repository.projects_subordinates_keyids
    keyid_to_keyval = self.repository.keyid_to_keyval

    for projects_subordinate in self.repository.projects_subordinates:
      # project names
      roles = sorted(self.repository.projects_subordinates_to_projects[
                                                        projects_subordinate])
      # project names to keyids
      role_to_keyids = {role:
                        self.repository.projects.get_keyids_for_project(role)
                        for role in roles}
      # project name to paths
      role_to_paths = {role: ['packages/*/{}/{}/*'.format(role[0], role)]
                       for role in roles}

      version = \
        self.repository.get_projects_subordinate_version(projects_subordinate)

      self.projects_subordinates_metadata[projects_subordinate] = \
        self.make_targets_metadata(keyids=keyids,
                                   keyid_to_keyval=keyid_to_keyval,
                                   roles=roles, role_to_keyids=role_to_keyids,
                                   role_to_paths=role_to_paths,
                                   version=version)

      self.projects_subordinates_metadata_json[projects_subordinate] = \
        self.jsonify(self.projects_subordinates_metadata[projects_subordinate])


  def make_release_metadata(self, keyids=(), meta={}, timestamp=0, version=0):
    return {
      'signatures': [
        {
          'keyid': keyid,
          'method': 'ed25519',
          'sig': self.__make_pseudo_signature(meta, timestamp, version)
        } for keyid in keyids
      ],
      'signed': {
        '_type': 'Release',
        # Expire a day from now, following PEP 458.
        'expires': self.__make_expiration_timestamp(timestamp, 1),
        'meta': meta,
        'version': version
      }
    }


  def make_snapshot_administrator_metadata(self, timestamp):
    raise NotImplementedError()


  def make_targets_metadata(self, keyid_to_keyval={}, keyids=(),
                            role_to_keyids={}, role_to_paths={}, roles=(),
                            targets={}, timestamp=0, version=0):
    return {
      'signatures': [
        {
          'keyid': keyid,
          'method': 'ed25519',
          'sig': self.__make_pseudo_signature(targets, timestamp, version)
        } for keyid in keyids
      ],
      'signed': {
        '_type': 'Targets',
        'delegations': {
          'keys': {
            keyid: {
              'keytype': 'ed25519',
              'keyval': {
                'public': keyid_to_keyval[keyid]
              }
            } for keyid in keyids for keyids in role_to_keyids.values()
          },
          'roles': [
            {
              'keyids': role_to_keyids[role],
              'name': 'packages/{}'.format(role),
              'paths': role_to_paths[role],
              'threshold': 1
            } for role in roles
          ]
        },
        # Expire a year from now, following PEP 458.
        'expires': self.__make_expiration_timestamp(timestamp, 365),
        'targets': targets,
        'version': version
      }
    }


  def mkdir(self, directory):
    try:
      os.makedirs(directory)
    except OSError as os_error:
      if os_error.errno != errno.EEXIST:
        raise


  def project_metadata_identifier(self, project_name):
    raise NotImplementedError()


  def reset_metadata(self):
    # str_of_project_name: dict_of_targets_metadata
    self.project_developer_metadata = {}
    # str_of_project_name: json.dumps(dict_of_targets_metadata)
    self.project_developer_metadata_json = {}

    # dict_of_targets_metadata
    self.projects_administrator_metadata = {}
    # json.dumps(dict_of_targets_metadata)
    self.projects_administrator_metadata_json = \
                            self.jsonify(self.projects_administrator_metadata)

    # str_of_role_name: dict_of_targets_metadata
    self.projects_subordinates_metadata = {}
    # str_of_role_name: json.dumps(dict_of_targets_metadata)
    self.projects_subordinates_metadata_json = {}

    # dict_of_snapshot_metadata
    self.snapshot_administrator_metadata = {}
    # json.dumps(dict_of_snapshot_metadata)
    self.snapshot_administrator_metadata_json = \
                  self.jsonify(self.snapshot_administrator_metadata)


  def rmdir(self, directory):
    try:
      shutil.rmtree(directory)
    except FileNotFoundError:
      pass


  # TODO:
  # 1. take care of inc version for:
  # 1.1. projects subordinates
  def release(self, timestamp):
    assert timestamp > 0

    logging.info('Making project developer metadata...')
    self.make_project_developer_metadata(timestamp)

    # TODO: best place to do this?
    if len(self.repository.projects.dirty) > 0:
      self.repository.release()

    #logging.info('...done. Making projects administrator metadata...')
    #self.make_projects_administrator_metadata()

    #logging.info('...done. Making projects subordinates metadata...')
    #self.make_projects_subordinates_metadata()

    logging.info('...done. Making snapshot administrator metadata...')
    self.make_snapshot_administrator_metadata(timestamp)

    logging.info('...done. Flushing all metadata...')
    self.flush_metadata(timestamp)

    logging.info('...done.')


  def write_json_to_disk(self, metadata_path, metadata_version, metadata_json,
                         overwrite=False):
    assert not metadata_path.startswith(self.metadata_directory)
    if isinstance(metadata_version, int):
      assert metadata_version > 0
    assert isinstance(metadata_json, bytes)

    metadata_path = os.path.join(self.metadata_directory, metadata_path)
    dirname, basename = os.path.split(metadata_path)
    self.mkdir(dirname)

    assert basename.endswith('.json')
    basename = '{}.{}.json'.format(basename[:-5], metadata_version)

    metadata_path = os.path.join(dirname, basename)

    if not os.path.exists(metadata_path) or overwrite:
      with open(metadata_path, 'wt') as metadata_file:
        metadata_file.write(metadata_json.decode('utf-8'))
      logging.debug('W {}'.format(metadata_path))


def write(log_filename, dirty_projects_cache_filepath,
          metadata_patch_length_cache_filepath, RepositoryClass,
          MetadataWriterClass, metadata_directory):
  logging.basicConfig(filename=log_filename, level=logging.DEBUG, filemode='w',
                      format=LOG_FORMAT)

  try:
    if os.path.isfile(dirty_projects_cache_filepath):
      os.remove(dirty_projects_cache_filepath)
    if os.path.isfile(metadata_patch_length_cache_filepath):
      os.remove(metadata_patch_length_cache_filepath)

    changelog_reader = ChangeLogReader()
    changelog_reader.read()

    repository = RepositoryClass(changelog_reader)

    metadata_writer = MetadataWriterClass(repository, metadata_directory)
    # The initial timestamp is right before the midnight of March 21 2014, the
    # day the log starts.
    prev_timestamp = unix_timestamp(2014, 3, 21)-1
    metadata_writer.release(prev_timestamp)

    # Instead of writing a snapshot every few minutes, just write a snapshot
    # whenever something actually changes.  Also, batch updates by timestamp.
    for curr_timestamp, changes in changelog_reader.aggregate().items():
      assert prev_timestamp < curr_timestamp
      for change in changes:
        logging.info('Change {} at timestamp {}'.format(change,
                                                        curr_timestamp))
        repository.update(change)
      metadata_writer.release(curr_timestamp)
      prev_timestamp = curr_timestamp

  except:
    logging.exception('WHAM!')
    raise
