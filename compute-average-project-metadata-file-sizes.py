#!/usr/bin/env python3


# 1st-party
import bz2
import json
import os
import sys


# 2nd-party
from nouns import METADATA_DIRECTORY, TUF_DIRECTORY


# 3rd-party
import jsonpatch


# Find the project with a recurring cost closest to the given average.
def find_project_with_avg_recurring_cost(FIRST_SNAPSHOT_FILEPATH,
                                         LAST_SNAPSHOT_FILEPATH,
                                         AVG_RECURRING_COST):
  with open(FIRST_SNAPSHOT_FILEPATH) as first_snapshot_file, \
       open(LAST_SNAPSHOT_FILEPATH) as last_snapshot_file:
    first_snapshot = json.load(first_snapshot_file)
    last_snapshot = json.load(last_snapshot_file)

  first_projects = first_snapshot['signed']['meta']
  last_projects = last_snapshot['signed']['meta']
  min_abs_diff = sys.maxsize
  project_with_min_abs_diff = None
  total_number_of_projects = 0

  for project_metadata_filepath, \
      first_project_metadata_identifier in first_projects.items():
    # Count this project only if it exists in both the first and last snapshots.
    last_project_metadata_identifier = \
                                    last_projects.get(project_metadata_filepath)
    if last_project_metadata_identifier:
      first_project_metadata = \
                    get_project_metadata_json(project_metadata_filepath,
                                              first_project_metadata_identifier)
      last_project_metadata = \
                     get_project_metadata_json(project_metadata_filepath,
                                               last_project_metadata_identifier)
      project_metadata_file_size = get_delta_size(first_project_metadata,
                                                  last_project_metadata)
      abs_diff = abs(project_metadata_file_size - AVG_RECURRING_COST)
      if abs_diff < min_abs_diff:
        min_abs_diff = abs_diff
        project_with_min_abs_diff = project_metadata_filepath
      total_number_of_projects += 1

  assert project_with_min_abs_diff
  print('{} has min abs diff to avg recurring cost: {:,} bytes'.\
        format(project_with_min_abs_diff, min_abs_diff))

# Why the last snapshot? Because we want to get the best estimate we can of
# the average project metadata file size, which should get better with a larger
# number of projects.
def get_avg_initial_cost(LAST_SNAPSHOT_FILEPATH,
                         output_filename='avg_initial_cost.txt'):
  with open(LAST_SNAPSHOT_FILEPATH) as last_snapshot_file:
    last_snapshot = json.load(last_snapshot_file)

  projects = last_snapshot['signed']['meta']
  total_project_metadata_file_size = 0
  max_project_metadata_file_size = -1

  with open(os.path.join(METADATA_DIRECTORY,
                         output_filename), 'wt') as output_file:
    for project_metadata_filepath, \
        project_metadata_identifier in projects.items():
      project_metadata = get_project_metadata_bytes(project_metadata_filepath,
                                                    project_metadata_identifier)
      project_metadata_file_size = len(bz2.compress(project_metadata))
      if project_metadata_file_size > max_project_metadata_file_size:
        max_project_metadata_file_size = project_metadata_file_size
      output_file.write('{}\n'.format(project_metadata_file_size))
      total_project_metadata_file_size += project_metadata_file_size

  avg_initial_cost = round(total_project_metadata_file_size / len(projects))
  print('Avg GPG/RSA initial cost = {:,} bytes'.\
        format(avg_initial_cost))
  print('Max GPG/RSA initial cost = {:,} bytes'\
        .format(max_project_metadata_file_size))
  return avg_initial_cost


# Compute the average recurring cost for a project metadata file that existed
# between the first and last snapshots.
def get_avg_recurring_cost(FIRST_SNAPSHOT_FILEPATH, LAST_SNAPSHOT_FILEPATH,
                           output_filename='avg_recurring_cost.txt'):
  with open(FIRST_SNAPSHOT_FILEPATH) as first_snapshot_file, \
       open(LAST_SNAPSHOT_FILEPATH) as last_snapshot_file:
    first_snapshot = json.load(first_snapshot_file)
    last_snapshot = json.load(last_snapshot_file)

  first_projects = first_snapshot['signed']['meta']
  last_projects = last_snapshot['signed']['meta']
  total_project_metadata_file_size = 0
  max_project_metadata_file_size = -1
  total_number_of_projects = 0

  with open(os.path.join(METADATA_DIRECTORY,
                         output_filename), 'wt') as output_file:
    for project_metadata_filepath, \
        first_project_metadata_identifier in first_projects.items():
      # Count this project only if it exists in both the first and last
      # snapshots.
      last_project_metadata_identifier = \
                                    last_projects.get(project_metadata_filepath)
      if last_project_metadata_identifier:
        first_project_metadata = \
                    get_project_metadata_json(project_metadata_filepath,
                                              first_project_metadata_identifier)
        last_project_metadata = \
                     get_project_metadata_json(project_metadata_filepath,
                                               last_project_metadata_identifier)
        project_metadata_file_size = get_delta_size(first_project_metadata,
                                                    last_project_metadata)
        if project_metadata_file_size > max_project_metadata_file_size:
          max_project_metadata_file_size = project_metadata_file_size
        output_file.write('{}\n'.format(project_metadata_file_size))
        total_project_metadata_file_size += project_metadata_file_size
        total_number_of_projects += 1

  avg_recurring_cost = round(total_project_metadata_file_size / \
                             total_number_of_projects)
  print('# of recurring projects: {:,}'.format(total_number_of_projects))
  print('Avg GPG/RSA recurring cost = {:,} bytes'.\
        format(avg_recurring_cost))
  print('Max GPG/RSA recurring cost = {:,} bytes'\
        .format(max_project_metadata_file_size))
  return avg_recurring_cost


def get_delta_size(prev, curr):
  patch = jsonpatch.make_patch(prev, curr)

  patch_str = str(patch)
  patch_str_length = len(patch_str)
  compressed_patch_str = bz2.compress(patch_str.encode('utf-8'))
  compressed_patch_str_length = len(compressed_patch_str)

  # If the patch is small enough, compression may increase bandwidth cost.
  return min(patch_str_length, compressed_patch_str_length)


def get_project_metadata_bytes(project_metadata_filepath,
                               project_metadata_identifier):
  return get_project_metadata_str(project_metadata_filepath,
                                  project_metadata_identifier).encode('utf-8')


def get_project_metadata_json(project_metadata_filepath,
                              project_metadata_identifier):
  return json.loads(get_project_metadata_str(project_metadata_filepath,
                                             project_metadata_identifier))


def get_project_metadata_str(project_metadata_filepath,
                             project_metadata_identifier):
  assert project_metadata_filepath.endswith('.json')
  project_metadata_filepath = '{}.{}{}'.format(project_metadata_filepath[:-5],
                                               project_metadata_identifier,
                                               '.json')
  project_metadata_filepath = os.path.join(TUF_DIRECTORY,
                                           project_metadata_filepath)
  with open(project_metadata_filepath) as project_metadata_file:
    return project_metadata_file.read()


if __name__ == '__main__':
  # It shouldn't matter whether we're looking at the project metadata for TUF or
  # any other security system, because they should all have the same project
  # metadata.
  FIRST_SNAPSHOT_FILEPATH = os.path.join(TUF_DIRECTORY,
                                         'snapshot.1395359999.json')
  LAST_SNAPSHOT_FILEPATH = os.path.join(TUF_DIRECTORY,
                                        'snapshot.1397951828.json')

  get_avg_initial_cost(LAST_SNAPSHOT_FILEPATH)
  print('')
  avg_recurring_cost = get_avg_recurring_cost(FIRST_SNAPSHOT_FILEPATH,
                                              LAST_SNAPSHOT_FILEPATH)
  print('')
  # There are minor differences due to nondeterminism in bz2 output, and I think
  # they are non-consequential.
  find_project_with_avg_recurring_cost(FIRST_SNAPSHOT_FILEPATH,
                                       LAST_SNAPSHOT_FILEPATH,
                                       avg_recurring_cost)
