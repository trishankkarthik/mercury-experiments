#!/usr/bin/env python3


# 1st-party
import bz2
import glob
import json
import os
import random


# 2nd-party
from nouns import MERCURY_DIRECTORY, MERCURY_NOHASH_DIRECTORY, \
                  METADATA_DIRECTORY, TUF_DIRECTORY


def avg_bz2_len_json(projects_metadata):
  total_size = 0
  # NOTE: keys are relative filenames, values are project metadata themselves
  for project_metadata in projects_metadata.values():
    total_size += bz2_len_json(project_metadata)
  return total_size / len(projects_metadata)


def bz2_len_json(metadata):
  return len(bz2.compress(jsonify(metadata)))


def tuf_version_bz2_len_json(projects_metadata):
  # 1. Transform each project metadata file into a project version metadata file
  # NOTE: Approximate the project version metadata file (i.e., a version
  # of the project metadata file that contains only the version number of
  # the actual project metadata file) by deleting everything but the version
  # number from the signed part of the message. The signatures will remain
  # the same; this is okay.
  new_projects_metadata = {}

  for project in projects_metadata:
    project_metadata = projects_metadata[project]
    new_project_metadata = {
      'signatures': project_metadata['signatures'],
      'signed': {
        'version': project_metadata['signed']['version']
      }
    }
    new_projects_metadata[project] = new_project_metadata

  # 2. Return the compressed size
  assert len(new_projects_metadata)==len(projects_metadata)
  return bz2_len_json(new_projects_metadata)


def jsonify(metadata):
  return json.dumps(metadata, indent=None, separators=(',', ':'),
                    sort_keys=True).encode('utf-8')


def compute(LAST_TIMESTAMP, NUMBER_OF_PROJECTS, SNAPSHOT_FILEPATH,
            projects_metadata_sizer, COST_FOR_NEW_USERS_FILEPATH):
  # 0. Reset PRNG
  random.seed(LAST_TIMESTAMP)

  # 1. C = {}
  COST = {}

  # 2. For every desired number of projects...
  for number_of_projects in NUMBER_OF_PROJECTS:
    # 2.1. s = the compressed size of S
    with open(SNAPSHOT_FILEPATH) as snapshot_file:
      snapshot = json.load(snapshot_file)

    # Trim the snapshot down to the number of projects.
    snapshot_meta = snapshot['signed']['meta']
    all_projects = set(snapshot_meta)
    number_of_projects = min(number_of_projects, len(all_projects))
    preserved_projects = set(random.sample(all_projects, number_of_projects))
    deleted_projects = all_projects-preserved_projects

    assert len(preserved_projects) == number_of_projects
    assert len(preserved_projects)+len(deleted_projects) == len(all_projects)
    for deleted_project in deleted_projects:
      del snapshot_meta[deleted_project]
    assert set(snapshot_meta) == preserved_projects

    # Get compressed snapshot metadata size.
    snapshot_metadata_size = bz2_len_json(snapshot)

    # 2.2. Collect all project metadata in a dictionary.
    projects_metadata = {}

    # 2.3. Read every project metadata P in S.
    metadata_directory = os.path.dirname(SNAPSHOT_FILEPATH)
    for project in preserved_projects:
      assert project.endswith('.json')
      project_metadata_identifier = snapshot_meta[project]
      # Kludge to workaround Mercury-hash.
      if isinstance(project_metadata_identifier, dict):
        project_metadata_identifier = project_metadata_identifier['hashes']\
                                                                 ['sha256']
      else:
        assert isinstance(project_metadata_identifier, int) or \
               isinstance(project_metadata_identifier, str)
      project_metadata_filepath = '{}.{}{}'.format(project[:-5],
                                                   project_metadata_identifier,
                                                   project[-5:])
      project_metadata_filepath = os.path.join(metadata_directory,
                                               project_metadata_filepath)
      with open(project_metadata_filepath) as project_metadata_file:
        project_metadata = json.load(project_metadata_file)

      projects_metadata[project] = project_metadata

    # 2.4. c = The compression of all project metadata in one shot.
    projects_metadata_size = projects_metadata_sizer(projects_metadata)
    # c = s + p
    metadata_size = {
      'project_metadata_length': projects_metadata_size,
      'snapshot_metadata_length': snapshot_metadata_size
    }

    # 2.5. C[S] = c
    COST[number_of_projects] = metadata_size
    print('{}: {}'.format(number_of_projects, metadata_size))

  # 3. Write C as JSON to file
  with open(COST_FOR_NEW_USERS_FILEPATH, 'w') as cost_json_file:
    json.dump(COST, cost_json_file, indent=1, sort_keys=True)


if __name__ == '__main__':
  NUMBER_OF_PROJECTS = [2**i for i in range(17)]
  # Why the last snapshot? Because we want *some* variation in version numbers
  # to get a realistic enough size for compressed version-snapshot metadata.
  LAST_TIMESTAMP = 1397951828
  SNAPSHOT_FILEPATH = 'snapshot.{}.json'.format(LAST_TIMESTAMP)

  print('MERCURY')
  MERCURY_SNAPSHOT_FILEPATH = os.path.join(MERCURY_DIRECTORY, SNAPSHOT_FILEPATH)
  MERCURY_COST_FOR_NEW_USERS_FILEPATH = \
                           os.path.join(METADATA_DIRECTORY,
                                        'vary-mercury-costs-for-new-users.json')
  compute(LAST_TIMESTAMP, NUMBER_OF_PROJECTS, MERCURY_SNAPSHOT_FILEPATH,
          avg_bz2_len_json, MERCURY_COST_FOR_NEW_USERS_FILEPATH)
  print('')

  print('MERCURY-NOHASH')
  MERCURY_NOHASH_SNAPSHOT_FILEPATH = os.path.join(MERCURY_NOHASH_DIRECTORY,
                                                  SNAPSHOT_FILEPATH)
  MERCURY_NOHASH_COST_FOR_NEW_USERS_FILEPATH = \
                    os.path.join(METADATA_DIRECTORY,
                                 'vary-mercury-nohash-costs-for-new-users.json')
  compute(LAST_TIMESTAMP, NUMBER_OF_PROJECTS, MERCURY_NOHASH_SNAPSHOT_FILEPATH,
          avg_bz2_len_json, MERCURY_NOHASH_COST_FOR_NEW_USERS_FILEPATH)
  print('')

  print('TUF')
  TUF_SNAPSHOT_FILEPATH = os.path.join(TUF_DIRECTORY, SNAPSHOT_FILEPATH)
  TUF_COST_FOR_NEW_USERS_FILEPATH = \
          os.path.join(METADATA_DIRECTORY, 'vary-tuf-costs-for-new-users.json')
  compute(LAST_TIMESTAMP, NUMBER_OF_PROJECTS, TUF_SNAPSHOT_FILEPATH,
          bz2_len_json, TUF_COST_FOR_NEW_USERS_FILEPATH)
  print('')

  print('TUF-VERSION')
  TUF_SNAPSHOT_FILEPATH = os.path.join(TUF_DIRECTORY, SNAPSHOT_FILEPATH)
  TUF_VERSION_COST_FOR_NEW_USERS_FILEPATH = \
                        os.path.join(METADATA_DIRECTORY,
                                    'vary-tuf-version-costs-for-new-users.json')
  compute(LAST_TIMESTAMP, NUMBER_OF_PROJECTS, TUF_SNAPSHOT_FILEPATH,
          tuf_version_bz2_len_json, TUF_VERSION_COST_FOR_NEW_USERS_FILEPATH)
  print('')
