#!/usr/bin/env python3


# 1st-party
import bz2
import glob
import json
import os


# 2nd-party
from nouns import METADATA_DIRECTORY, TUF_COST_FOR_NEW_USERS_FILEPATH, \
                  TUF_DIRECTORY


SNAPSHOTS_FILEPATH = os.path.join(TUF_DIRECTORY, 'snapshot.*.json')


def precompute():
  # Cache of all project metadata (identified by hashes).
  PROJECT_METADATA = {}

  # 1. C = {}
  COST = {}

  # 2. For every version S of snapshot metadata:
  SNAPSHOTS = sorted(glob.glob(SNAPSHOTS_FILEPATH))
  for SNAPSHOT in SNAPSHOTS:
    # 2.1. s = the compressed size of S
    with open(SNAPSHOT) as snapshot_file:
      snapshot_json = snapshot_file.read()
    snapshot_metadata_size = len(bz2.compress(snapshot_json.encode('utf-8')))
    PROJECTS = json.loads(snapshot_json)['signed']['meta']

    # 2.2. Collect all project metadata in a dictionary.
    projects_metadata = {}

    # 2.3. Read every project metadata P in S.
    for PROJECT, HASH in PROJECTS.items():
      assert PROJECT.endswith('.json')
      project_metadata_filepath = '{}.{}{}'.format(PROJECT[:-5], HASH,
                                                   PROJECT[-5:])
      project_metadata = PROJECT_METADATA.get(project_metadata_filepath)

      if not project_metadata:
        project_metadata_filepath = os.path.join(TUF_DIRECTORY,
                                                 project_metadata_filepath)
        with open(project_metadata_filepath) as project_metadata_file:
          project_metadata = json.load(project_metadata_file)
        assert TUF_DIRECTORY.endswith('/')
        project_metadata_filepath = \
                                  project_metadata_filepath[len(TUF_DIRECTORY):]
        PROJECT_METADATA[project_metadata_filepath] = project_metadata

      assert project_metadata
      projects_metadata[PROJECT] = project_metadata

    # 2.4. c = The compression of all project metadata in one shot.
    projects_metadata_json = json.dumps(projects_metadata, indent=None,
                                        separators=(',', ':'), sort_keys=True)
    projects_metadata_size = \
                      len(bz2.compress(projects_metadata_json.encode('utf-8')))
    # c = s + p
    metadata_size = {
      'project_metadata_length': projects_metadata_size,
      'snapshot_metadata_length': snapshot_metadata_size
    }

    # 2.5. C[S] = c
    snapshot_filename = os.path.basename(SNAPSHOT)
    COST[snapshot_filename] = metadata_size
    print('{}: {}'.format(snapshot_filename, metadata_size))

  # 3. Write C as JSON to file
  with open(TUF_COST_FOR_NEW_USERS_FILEPATH, 'w') as cost_json_file:
    json.dump(COST, cost_json_file, indent=1, sort_keys=True)


if __name__ == '__main__':
  precompute()
