

# 1st-party
import bz2
import collections
import csv
import glob
import json
import logging
import math
import os
import re


# 2nd-party
from nouns import FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE, \
                  LOG_FORMAT, REQUESTS_FILENAME, TIME_LIMIT_IN_SECONDS
from projects import Projects


# 3rd-party
import jsonpatch


# If you want to *cache* ALL snapshot metadata in RAM,
# then set this flag to True.
# Otherwise, we will load every snapshot metadata file from disk,
# and leave the caching to the OS.
CACHE_SNAPSHOT = False
NUMBER_OF_SECONDS_IN_A_DAY = 24*60*60
SNAPSHOTS_ARE_EXHAUSTED = False
# The experiment is valid since only the following Unix timestamp.
SINCE_TIMESTAMP = 1395360000


class MetadataReader:


  def __init__(self, ip_address):
    self.__ip_address = ip_address

    # For computing the difference between previous and current versions of
    # metadata.
    # NOTE: This is the previous snapshot metadata before the previous
    # snapshot metadata!
    self._prev_prev_snapshot_metadata_relpath = None
    # NOTE: No one is assumed to start with a copy of snapshot metadata.
    self._prev_snapshot_metadata_relpath = None

    # user-specific cache to memoize metadata file lengths
    # {str (absolute filename)}
    self._metadata_and_package_cache = set()


  # Secure lazy evaluation à la Mercury.
  def _baseline_charge(self, curr_snapshot_timestamp, url):
    assert url.startswith('/')
    package_relpath = url[1:]
    package_cost = PackageCost()

    # 1. Fetch the latest snapshot metadata, if not already cached.
    curr_snapshot_metadata_relpath = \
                            'snapshot.{}.json'.format(curr_snapshot_timestamp)
    snapshot_metadata_length = \
            self.get_cached_metadata_cost(self._prev_snapshot_metadata_relpath,
                                          curr_snapshot_metadata_relpath)
    logging.debug('Prev, curr snapshot = {}, {}'\
                  .format(self._prev_snapshot_metadata_relpath,
                          curr_snapshot_metadata_relpath))
    logging.debug('Snapshot metadata length = {:,}'\
                  .format(snapshot_metadata_length))
    self._prev_prev_snapshot_metadata_relpath = \
                                          self._prev_snapshot_metadata_relpath
    self._prev_snapshot_metadata_relpath = curr_snapshot_metadata_relpath

    package_cost.snapshot_metadata_length = snapshot_metadata_length
    snapshot_metadata = self._read_snapshot(curr_snapshot_metadata_relpath)

    project_name = Projects.get_project_name_from_package(url)
    project_metadata_relpath = 'packages/{}.json'.format(project_name)

    # Does the project of the desired package exist in this snapshot?
    if project_metadata_relpath in snapshot_metadata:
      # What are the previous and current versions of this project?
      prev_project_metadata_relpath = \
              self._get_prev_project_metadata_relpath(project_metadata_relpath,
                                                      project_name)
      project_metadata_identifier = \
               self._get_project_metadata_identifier(snapshot_metadata[\
                                                      project_metadata_relpath])
      curr_project_metadata_relpath = 'packages/{}.{}.json'\
                                      .format(project_name,
                                              project_metadata_identifier)
      logging.debug('Prev, curr project = {}, {}'\
                    .format(prev_project_metadata_relpath,
                            curr_project_metadata_relpath))
      self._set_prev_project_metadata_relpath(project_metadata_relpath,
                                              curr_project_metadata_relpath)

      # 2. Fetch the latest project metadata, if not already cached, according
      # to the latest snapshot metadata.
      project_metadata_length = \
                  self.get_cached_metadata_cost(prev_project_metadata_relpath,
                                                curr_project_metadata_relpath)
      logging.debug('Project metadata length = {:,}'\
                    .format(project_metadata_length))
      package_cost.add_project_metadata_length(project_metadata_length)
      # Find the package itself.
      project_metadata = self._read_project(curr_project_metadata_relpath)
      package_metadata = project_metadata.get(package_relpath)

      # Does the desired package itself exist now in the project?
      if package_metadata:
        # 4. Fetch the package itself, according to the latest project
        # metadata.
        package_length = package_metadata['length']
        package_cost.package_length = \
                  self.get_cached_package_cost(package_relpath, package_length)
        logging.debug('Package length = {:,}'\
                      .format(package_length))
        logging.debug('Package cost = {}'.format(package_cost))
        return package_cost
      else:
        raise UnknownPackage(package_relpath)
    else:
      raise UnknownProject(project_name)


  def _get_dirty_projects(self, patch):
    dirty_projects = {}

    for op in patch:
      operation = op['op']

      if operation in {'add', 'replace'}:
        path = op['path']
        # If there was no initial snapshot.
        if path == '/signed':
          assert operation == 'add'
          meta = op['value']['meta']
          for project_metadata_relpath, \
              project_metadata_identifier in meta.items():
            dirty_projects[project_metadata_relpath] = \
              self._get_project_metadata_identifier(project_metadata_identifier)
          break

        # If there was an initial snapshot.
        elif path.startswith('/signed/meta/packages'):
          # http://tools.ietf.org/html/rfc6901
          project_metadata_relpath = path[13:].replace('~1', '/')
          assert project_metadata_relpath.startswith('packages/')
          assert project_metadata_relpath.endswith('.json')
          dirty_projects[project_metadata_relpath] = \
                              self._get_project_metadata_identifier(op['value'])
      else:
        assert operation == 'remove'

    assert len(dirty_projects) > 0
    return dirty_projects


  # What is the previous project metadata version for this project?
  def _get_prev_project_metadata_relpath(self, project_metadata_relpath,
                                         project_name):
    raise NotImplementedError()


  # NOTE: Kludge to accommodate mercury-hash, which has both hashes and
  # version numbers.
  @classmethod
  def _get_project_metadata_identifier(cls, project_metadata_identifier):
    if isinstance(project_metadata_identifier, dict):
      logging.debug('mercury-hash')
      return project_metadata_identifier['hashes']['sha256']
    else:
      assert isinstance(project_metadata_identifier, int) or \
             isinstance(project_metadata_identifier, str)
      return project_metadata_identifier


  # Load from cache the dirty projects present in snapshot diff.
  def _load_dirty_projects(self, curr_metadata_relpath, key): pass


  @classmethod
  def _read_metadata(cls, metadata_relpath):
    metadata = cls._METADATA_CACHE.get(metadata_relpath)

    if not metadata:
      with open(cls.__get_metadata_abspath(metadata_relpath)) as metadata_file:
        metadata = json.load(metadata_file)
        cls._METADATA_CACHE[metadata_relpath] = metadata

    return metadata

  @classmethod
  def _read_project(cls, project_metadata_relpath):
    return cls._read_metadata(project_metadata_relpath)['signed']['targets']


  @classmethod
  def _read_snapshot(cls, snapshot_metadata_relpath):
    return cls._read_metadata(snapshot_metadata_relpath)['signed']['meta']


  # Clear cache of dirty projects present in snapshot diff.
  def _reset_dirty_projects(self, curr_metadata_relpath): pass


  # Set the previous project metadata version for this project.
  def _set_prev_project_metadata_relpath(self, project_metadata_relpath,
                                         curr_project_metadata_relpath): pass


  # Store in cache the dirty projects present in snapshot diff.
  def _store_dirty_projects(self, curr_metadata_relpath, key, patch): pass


  @classmethod
  def __current_and_next_snapshot_timestamps_generator(cls):
    # TODO: Replace global variable with an additional return variable.
    global SNAPSHOTS_ARE_EXHAUSTED
    timestamps = cls.__SNAPSHOT_TIMESTAMPS
    f = FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE
    assert f > 0

    last_timestamp = None
    number_of_timestamps = len(timestamps)

    for i in range(1, number_of_timestamps):
      timestamp = timestamps[i]
      time_delta = timestamp - SINCE_TIMESTAMP
      f_timestamp = SINCE_TIMESTAMP + (f * time_delta)
      # The user who issued the last package request in the month could only
      # have seen f_timestamp if it was produced before the time the user
      # issued the request.
      if f_timestamp >= 1397951999:
        break
      else:
        last_timestamp = timestamp

    assert last_timestamp

    while True:
      logging.debug('curr, next snapshots = {}, {}'.format(last_timestamp,
                                                           last_timestamp))
      yield last_timestamp, last_timestamp

    # max_index = len(timestamps)-1
    # realtime_curr_index = 0
    # realtime_next_index = 1
    #
    # while True:
    #   curr_index = min(realtime_curr_index, max_index)
    #   curr_timestamp = timestamps[curr_index]
    #
    #   next_index = min(realtime_next_index, max_index)
    #   next_timestamp = timestamps[next_index]
    #   time_delta = next_timestamp - SINCE_TIMESTAMP
    #   next_timestamp = SINCE_TIMESTAMP + (f * time_delta)
    #
    #   logging.debug('curr, next snapshots = {}, {}'.format(curr_timestamp,
    #                                                        next_timestamp))
    #   yield curr_timestamp, next_timestamp
    #
    #   realtime_curr_index += 1
    #   # Snapshots are truly exhausted only when f < 1.
    #   if realtime_curr_index == max_index and f < 1:
    #     SNAPSHOTS_ARE_EXHAUSTED = True
    #   realtime_next_index += 1


  @classmethod
  def __get_metadata_abspath(cls, metadata_relpath):
    return os.path.join(cls.__METADATA_DIRECTORY, metadata_relpath)


  @classmethod
  def __get_metadata_relpath(cls, metadata_abspath):
    return metadata_abspath[len(cls.__METADATA_DIRECTORY):]


  def __get_patch_length(self, prev_metadata_relpath, curr_metadata_relpath):
    key = '{}:{}'.format(prev_metadata_relpath, curr_metadata_relpath)

    # If we have already cached the difference, use that.
    if key in self.__METADATA_PATCH_LENGTH_CACHE:
      self._load_dirty_projects(curr_metadata_relpath, key)
      cost = self.__METADATA_PATCH_LENGTH_CACHE[key]

    # Otherwise, compute the difference.
    else:
      # Either get the previous file, if any, or start from scratch.
      if prev_metadata_relpath:
        prev = self._read_metadata(prev_metadata_relpath)
      else:
        prev = {}

      curr = self._read_metadata(curr_metadata_relpath)
      patch = jsonpatch.make_patch(prev, curr)
      self._store_dirty_projects(curr_metadata_relpath, key, patch)

      patch_str = str(patch)
      patch_str_length = len(patch_str)
      compressed_patch_str = bz2.compress(patch_str.encode('utf-8'))
      compressed_patch_str_length = len(compressed_patch_str)

      # If the patch is small enough, compression may increase bandwidth cost.
      cost = min(patch_str_length, compressed_patch_str_length)
      self.__METADATA_PATCH_LENGTH_CACHE[key] = cost

    return cost


  @classmethod
  def __setup_project_metadata(cls):
    project_metadata_abspaths = \
              sorted(glob.glob(cls.__get_metadata_abspath('packages/*.json')))

    for project_metadata_abspath in project_metadata_abspaths:
      with open(project_metadata_abspath) as project_metadata_file:
        project_metadata = json.load(project_metadata_file)
        project_metadata_relpath = \
                        cls.__get_metadata_relpath(project_metadata_abspath)
        assert project_metadata_relpath not in cls._METADATA_CACHE
        cls._METADATA_CACHE[project_metadata_relpath] = project_metadata


  @classmethod
  def __setup_snapshot_metadata(cls):
    prev_timestamp = 0
    snapshot_metadata_abspaths = \
              sorted(glob.glob(cls.__get_metadata_abspath('snapshot.*.json')))

    for snapshot_metadata_abspath in snapshot_metadata_abspaths:
      snapshot_metadata_relpath = \
                        cls.__get_metadata_relpath(snapshot_metadata_abspath)
      curr_timestamp = int(re.match('snapshot.(\d+).json',
                                    snapshot_metadata_relpath).group(1))
      assert prev_timestamp < curr_timestamp

      if TIME_LIMIT_IN_SECONDS and curr_timestamp > SINCE_TIMESTAMP+\
                                                    TIME_LIMIT_IN_SECONDS:
        break
      else:
        cls.__SNAPSHOT_TIMESTAMPS.append(curr_timestamp)
        prev_timestamp = curr_timestamp

        # TODO: Cache only snapshot metadata that will be actually be used.
        if CACHE_SNAPSHOT:
          with open(snapshot_metadata_abspath) as snapshot_metadata_file:
            snapshot_metadata = json.load(snapshot_metadata_file)
            assert snapshot_metadata_relpath not in cls._METADATA_CACHE
            cls._METADATA_CACHE[snapshot_metadata_relpath] = snapshot_metadata

        logging.info(snapshot_metadata_relpath)


  # For new users.
  def new_charge(self, curr_snapshot_timestamp, url):
    raise NotImplementedError()


  # For returning users.
  def return_charge(self, curr_snapshot_timestamp, url):
    raise NotImplementedError()


  def get_cached_metadata_cost(self, prev_metadata_relpath,
                               curr_metadata_relpath):
    # Has this metadata file been seen before?
    if curr_metadata_relpath in self._metadata_and_package_cache or \
       prev_metadata_relpath == curr_metadata_relpath:
      logging.debug('{} HIT {}'.format(self.__ip_address,
                                       curr_metadata_relpath))
      self._reset_dirty_projects(curr_metadata_relpath)
      return 0

    else:
      logging.debug('{} MISS {}'.format(self.__ip_address,
                                        curr_metadata_relpath))
      # Compute the difference, if possible; otherwise, the absolute cost.
      cached_cost = self.__get_patch_length(prev_metadata_relpath,
                                            curr_metadata_relpath)
      # If not, note this metadata file in this user/instance.
      self._metadata_and_package_cache.add(curr_metadata_relpath)
      return cached_cost


  # FIXME: What if the same package has been updated in place?
  def get_cached_package_cost(self, package_relpath, cached_cost):
    assert cached_cost >= 0

    # Has this package been seen before?
    if package_relpath in self._metadata_and_package_cache:
      logging.debug('{} HIT {}'.format(self.__ip_address, package_relpath))
      return 0

    else:
      logging.debug('{} MISS {}'.format(self.__ip_address, package_relpath))
      # If not, note this package in this user/instance.
      self._metadata_and_package_cache.add(package_relpath)
      return cached_cost


  @classmethod
  def get_current_and_next_snapshot_timestamps(cls):
    return next(cls.__CURRENT_AND_NEXT_SNAPSHOT_TIMESTAMPS_GENERATOR)


  @classmethod
  def setup(cls, metadata_directory, metadata_patch_length_cache_filepath,
            dirty_projects_cache_filepath):
    assert metadata_directory.endswith('/')
    assert os.path.isdir(metadata_directory)
    cls.__METADATA_DIRECTORY = metadata_directory

    # str (metadata relpath): dict (metadata)
    cls._METADATA_CACHE = {}

    # str (prev + curr metadata relpath): int (file length > -1)
    if os.path.isfile(metadata_patch_length_cache_filepath):
      with open(metadata_patch_length_cache_filepath) as \
                                              metadata_patch_length_cache_file:
        logging.debug('READ {}'.format(metadata_patch_length_cache_filepath))
        cls.__METADATA_PATCH_LENGTH_CACHE = \
                                    json.load(metadata_patch_length_cache_file)
    else:
      logging.debug('NO {}'.format(metadata_patch_length_cache_filepath))
      cls.__METADATA_PATCH_LENGTH_CACHE = {}

    # str (prev + curr metadata relpath): str/int (project_metadata_identifier)
    if os.path.isfile(dirty_projects_cache_filepath):
      with open(dirty_projects_cache_filepath) as dirty_projects_cache_file:
        logging.debug('READ {}'.format(dirty_projects_cache_filepath))
        cls._DIRTY_PROJECTS_CACHE = json.load(dirty_projects_cache_file)
    else:
      logging.debug('NO {}'.format(dirty_projects_cache_filepath))
      cls._DIRTY_PROJECTS_CACHE = {}

    logging.info('Setup project metadata...')
    cls.__setup_project_metadata()
    logging.info('...done.')

    # str (metadata relpath): dict (snapshot metadata)
    logging.info('Setup snapshot metadata...')
    # [int (UNIX timestamp > 0)]
    cls.__SNAPSHOT_TIMESTAMPS = []
    cls.__CURRENT_AND_NEXT_SNAPSHOT_TIMESTAMPS_GENERATOR = \
                        cls.__current_and_next_snapshot_timestamps_generator()
    cls.__setup_snapshot_metadata()
    logging.info('...done.')


  @classmethod
  def teardown(cls, metadata_patch_length_cache_filepath,
               dirty_projects_cache_filepath):
    if not os.path.isfile(metadata_patch_length_cache_filepath):
      with open(metadata_patch_length_cache_filepath, 'w') as \
                                              metadata_patch_length_cache_file:
        json.dump(cls.__METADATA_PATCH_LENGTH_CACHE,
                  metadata_patch_length_cache_file, indent=1, sort_keys=True)
      logging.debug('WROTE {}'.format(metadata_patch_length_cache_filepath))

    if not os.path.isfile(dirty_projects_cache_filepath):
      with open(dirty_projects_cache_filepath, 'w') as \
                                                      dirty_projects_cache_file:
        json.dump(cls._DIRTY_PROJECTS_CACHE, dirty_projects_cache_file,
                  indent=1, sort_keys=True)
      logging.debug('WROTE {}'.format(dirty_projects_cache_filepath))


class PackageCost:


  def __init__(self, package_length=0, project_metadata_length=0,
               snapshot_metadata_length=0):
    # int (length > -1)
    self.__package_length = package_length

    # int (length > -1)
    self.__project_metadata_length = project_metadata_length

    # int (length > -1)
    self.__snapshot_metadata_length = snapshot_metadata_length


  def __repr__(self):
    return '{"package_length": '+\
            '{:,}'.format(self.__package_length)+\
            ', '+\
            '"project_metadata_length": '+\
            '{:,}'.format(self.__project_metadata_length)+\
            ', '+\
            '"snapshot_metadata_length": '+\
            '{:,}'.format(self.__snapshot_metadata_length)+\
            '}'


  # https://docs.python.org/3/reference/datamodel.html#object.__add__
  def __add__(self, other):
    package_length = self.package_length + other.package_length
    project_metadata_length = self.project_metadata_length + \
                              other.project_metadata_length
    snapshot_metadata_length = self.snapshot_metadata_length + \
                               other.snapshot_metadata_length
    return PackageCost(package_length, project_metadata_length,
                       snapshot_metadata_length)


  # https://docs.python.org/3/reference/datamodel.html#object.__iadd__
  def __iadd__(self, other):
    self.__package_length += other.package_length
    self.__project_metadata_length += other.project_metadata_length
    self.__snapshot_metadata_length += other.snapshot_metadata_length
    return self


  def add_project_metadata_length(self, project_metadata_length):
    assert project_metadata_length >= 0
    self.__project_metadata_length += project_metadata_length


  @property
  def package_length(self):
    return self.__package_length


  @package_length.setter
  def package_length(self, package_length):
    assert package_length >= 0
    self.__package_length = package_length


  @property
  def project_metadata_length(self):
    return self.__project_metadata_length


  @property
  def snapshot_metadata_length(self):
    return self.__snapshot_metadata_length


  @snapshot_metadata_length.setter
  def snapshot_metadata_length(self, snapshot_metadata_length):
    assert snapshot_metadata_length >= 0
    self.__snapshot_metadata_length = snapshot_metadata_length


class PackageCostEncoder(json.JSONEncoder):


  @classmethod
  def encode_package_cost(cls, obj):
    assert isinstance(obj, PackageCost)
    return {
      'package_length': obj.package_length,
      'project_metadata_length': obj.project_metadata_length,
      'snapshot_metadata_length': obj.snapshot_metadata_length
    }


  def default(self, obj):
    if isinstance(obj, PackageCost):
      return self.encode_package_cost(obj)
    else:
      # Let the base class default method raise the TypeError
      return json.JSONEncoder.default(self, obj)


class UnknownPackage(Exception): pass
class UnknownProject(Exception): pass


def count(metadata_reader_class, output_filename):
  # str (user-agent@ip-address): MetadataReader (user)
  metadata_readers = {}
  # The total metadata+package costs for new users.
  new_package_cost = PackageCost()
  # The total metadata+package costs for returning users.
  return_package_cost = PackageCost()

  missed_requests, total_requests = 0, 0
  missed_packages = set()
  prev_user_timestamp = 0
  prev_day_number = 0

  curr_snapshot_timestamp, next_snapshot_timestamp = \
              metadata_reader_class.get_current_and_next_snapshot_timestamps()

  if os.path.exists(output_filename):
    os.remove(output_filename)
    logging.debug('Deleted {}'.format(output_filename))

  with open(REQUESTS_FILENAME, 'rt') as requests_file:
    requests_file = csv.reader(requests_file)

    for curr_user_timestamp, ip_address, url, user_agent in requests_file:
      curr_user_timestamp = int(curr_user_timestamp)

      # If we are out of time or new snapshots, then let's stop.
      time_limit_is_up = TIME_LIMIT_IN_SECONDS and \
                         curr_user_timestamp > SINCE_TIMESTAMP + \
                                               TIME_LIMIT_IN_SECONDS
      if time_limit_is_up or SNAPSHOTS_ARE_EXHAUSTED: break

      # We must be going forward, or staying where we are, in time.
      assert prev_user_timestamp <= curr_user_timestamp
      prev_user_timestamp = curr_user_timestamp
      # Set the current snapshot timestamp to the next one if the next
      # snapshot timestamp is already strictly older than the user timestamp.
      if curr_user_timestamp > next_snapshot_timestamp:
        logging.debug('advance snapshot: {} > {}'\
                      .format(curr_user_timestamp, next_snapshot_timestamp))
        curr_snapshot_timestamp, next_snapshot_timestamp = \
            metadata_reader_class.get_current_and_next_snapshot_timestamps()

      try:
        logging.debug('USER {}'.format(ip_address))
        if ip_address in metadata_readers:
          metadata_reader = metadata_readers[ip_address]
          return_package_cost += \
                    metadata_reader.return_charge(curr_snapshot_timestamp, url)
        else:
          metadata_reader = metadata_reader_class(ip_address)
          metadata_readers[ip_address] = metadata_reader
          new_package_cost += \
                      metadata_reader.new_charge(curr_snapshot_timestamp, url)

      # FIXME: But should we count the metadata cost anyway?
      except (UnknownPackage, UnknownProject):
        missed_packages.add(url)
        missed_requests += 1
      else:
        curr_day_number = (curr_user_timestamp-SINCE_TIMESTAMP) // \
                           NUMBER_OF_SECONDS_IN_A_DAY
        logging.debug('Day {}: {}'.format(curr_day_number,
                                          new_package_cost+\
                                          return_package_cost))
        if curr_day_number > prev_day_number:
          elapsed_time = prev_user_timestamp - SINCE_TIMESTAMP
          write(new_package_cost, return_package_cost, curr_day_number,
                elapsed_time, output_filename)
          prev_day_number = curr_day_number

      finally:
        total_requests += 1
        assert missed_requests <= total_requests
        logging.info('Total requests: {:,}'.format(total_requests))
        logging.info('')

  missed_percentage = (missed_requests/total_requests)*100
  logging.info('{}% missed requests'.format(missed_percentage))
  logging.info('Missed these packages: {}'.format(sorted(missed_packages)))

  logging.info('Day {}'.format(curr_day_number))
  logging.info('New: {}'.format(new_package_cost))
  logging.info('Return: {}'.format(return_package_cost))
  logging.info('Total: {}'.format(new_package_cost+return_package_cost))
  elapsed_time = prev_user_timestamp - SINCE_TIMESTAMP
  write(new_package_cost, return_package_cost, curr_day_number, elapsed_time,
        output_filename)


def read(log_filename, MetadataReaderClass, metadata_directory,
         metadata_patch_length_cache_filepath, dirty_projects_cache_filepath,
         output_filename):
  logging.basicConfig(filename=log_filename, level=logging.DEBUG, filemode='w',
                      format=LOG_FORMAT)

  try:
    MetadataReaderClass.setup(metadata_directory,
                              metadata_patch_length_cache_filepath,
                              dirty_projects_cache_filepath)
    count(MetadataReaderClass, output_filename)
    MetadataReaderClass.teardown(metadata_patch_length_cache_filepath,
                                 dirty_projects_cache_filepath)

  except:
    logging.exception('MEOW!')
    raise


def write(new_package_cost, return_package_cost, day_number, elapsed_time,
          output_filename):
  if os.path.exists(output_filename):
    with open(output_filename, 'r') as output_file:
      daily_costs = json.load(output_file)
  else:
    daily_costs = {}

  # Oh, you want to know why we're explicitly converting an int to a str?
  # Because Python 3 gets confused about sorting str and int keys.
  # https://bugs.python.org/issue25457
  day_number_str = str(day_number)
  daily_costs[day_number_str] = {
    'elapsed_time': elapsed_time,
    'new': PackageCostEncoder.encode_package_cost(new_package_cost),
    'return': PackageCostEncoder.encode_package_cost(return_package_cost)
  }

  with open(output_filename, 'w') as output_file:
    json.dump(daily_costs, output_file, indent=1, sort_keys=True)
