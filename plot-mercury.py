#!/usr/bin/env python3


# 1st-party
import json
import os


# 2nd-party
from nouns import METADATA_DIRECTORY


# 3rd-party
import matplotlib
# Force matplotlib to not use any Xwindows backend.
# http://stackoverflow.com/a/3054314
matplotlib.use('Agg')
# No Type 3 fonts in figures, as per ATC 2017 requirements.
# http://phyletica.org/matplotlib-fonts/
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as pyplot
import numpy
import scipy.stats


def plot_vary_number_of_new_projects():
  MIN_X, MAX_X = 5, 19
  MIN_Y, MAX_Y = 2, 9

  # INPUT
  TUF_COST_FOR_NEW_USERS_FILEPATH = \
          os.path.join(METADATA_DIRECTORY, 'vary-tuf-costs-for-new-users.json')
  TUF_VERSION_COST_FOR_NEW_USERS_FILEPATH = \
                       os.path.join(METADATA_DIRECTORY,
                                    'vary-tuf-version-costs-for-new-users.json')
  MERCURY_COST_FOR_NEW_USERS_FILEPATH = \
                           os.path.join(METADATA_DIRECTORY,
                                        'vary-mercury-costs-for-new-users.json')
  MERCURY_NOHASH_COST_FOR_NEW_USERS_FILEPATH = \
                    os.path.join(METADATA_DIRECTORY,
                                 'vary-mercury-nohash-costs-for-new-users.json')

  with open(TUF_COST_FOR_NEW_USERS_FILEPATH) as tuf_cost_for_new_users_file:
    tuf_cost_for_new_users = json.load(tuf_cost_for_new_users_file)

  with open(TUF_VERSION_COST_FOR_NEW_USERS_FILEPATH) as \
                                            tuf_version_cost_for_new_users_file:
    tuf_version_cost_for_new_users = \
                                  json.load(tuf_version_cost_for_new_users_file)

  with open(MERCURY_COST_FOR_NEW_USERS_FILEPATH) as \
                                                mercury_cost_for_new_users_file:
    mercury_cost_for_new_users = json.load(mercury_cost_for_new_users_file)

  with open(MERCURY_NOHASH_COST_FOR_NEW_USERS_FILEPATH) as \
                                         mercury_nohash_cost_for_new_users_file:
    mercury_nohash_cost_for_new_users = \
                               json.load(mercury_nohash_cost_for_new_users_file)

  # All must have the same numbers of projects
  assert tuf_cost_for_new_users.keys() == mercury_cost_for_new_users.keys()
  assert mercury_cost_for_new_users.keys() == \
         mercury_nohash_cost_for_new_users.keys()
  assert mercury_nohash_cost_for_new_users.keys() == \
         tuf_version_cost_for_new_users.keys()
  NUMBER_OF_PROJECTS = sorted(int(n) for n in tuf_cost_for_new_users)
  # NOTE: Throw out results when n is too small.
  NUMBER_OF_PROJECTS = [n for n in NUMBER_OF_PROJECTS if n >= 2**MIN_X]

  mercury_project_metadata_length = []
  mercury_snapshot_metadata_length = []
  mercury_metadata_length = []

  mercury_nohash_project_metadata_length = []
  mercury_nohash_snapshot_metadata_length = []
  mercury_nohash_metadata_length = []

  tuf_project_metadata_length = []
  tuf_snapshot_metadata_length = []
  tuf_metadata_length = []

  tuf_version_project_metadata_length = []
  tuf_version_snapshot_metadata_length = []
  tuf_version_metadata_length = []

  for n in NUMBER_OF_PROJECTS:
    n = str(n)

    key = 'project_metadata_length'
    mercury_project_metadata_length.append(mercury_cost_for_new_users[n][key])
    mercury_nohash_project_metadata_length.\
                               append(mercury_nohash_cost_for_new_users[n][key])
    tuf_project_metadata_length.append(tuf_cost_for_new_users[n][key])
    tuf_version_project_metadata_length.\
                                  append(tuf_version_cost_for_new_users[n][key])

    key = 'snapshot_metadata_length'
    mercury_snapshot_metadata_length.append(mercury_cost_for_new_users[n][key])
    mercury_nohash_snapshot_metadata_length.\
                               append(mercury_nohash_cost_for_new_users[n][key])
    tuf_snapshot_metadata_length.append(tuf_cost_for_new_users[n][key])
    tuf_version_snapshot_metadata_length.\
                                  append(tuf_version_cost_for_new_users[n][key])

  assert len(mercury_project_metadata_length) == \
         len(mercury_nohash_project_metadata_length)
  assert len(mercury_nohash_project_metadata_length) == \
         len(tuf_project_metadata_length)
  assert len(tuf_project_metadata_length) == \
         len(tuf_version_project_metadata_length)
  assert len(mercury_project_metadata_length) == len(NUMBER_OF_PROJECTS)

  assert len(mercury_snapshot_metadata_length) == \
         len(mercury_nohash_snapshot_metadata_length)
  assert len(mercury_nohash_snapshot_metadata_length) == \
         len(tuf_snapshot_metadata_length)
  assert len(tuf_snapshot_metadata_length) == \
         len(tuf_version_snapshot_metadata_length)
  assert len(mercury_snapshot_metadata_length) == len(NUMBER_OF_PROJECTS)

  # Produce tallies of metadata for each system.
  for i in range(len(NUMBER_OF_PROJECTS)):
    mercury_total_length = mercury_snapshot_metadata_length[i] + \
                           mercury_project_metadata_length[i]
    mercury_metadata_length.append(mercury_total_length)

    mercury_nohash_total_length = mercury_nohash_snapshot_metadata_length[i] + \
                                  mercury_nohash_project_metadata_length[i]
    mercury_nohash_metadata_length.append(mercury_nohash_total_length)

    tuf_version_total_length = tuf_version_snapshot_metadata_length[i] + \
                               tuf_version_project_metadata_length[i]
    tuf_version_metadata_length.append(tuf_version_total_length)

    tuf_total_length = tuf_snapshot_metadata_length[i] + \
                       tuf_project_metadata_length[i]
    tuf_metadata_length.append(tuf_total_length)

  assert len(mercury_metadata_length) == len(mercury_nohash_metadata_length)
  assert len(mercury_nohash_metadata_length) == len(tuf_metadata_length)
  assert len(tuf_metadata_length) == len(tuf_version_metadata_length)

  # http://stackoverflow.com/a/30670983
  x1 = numpy.log2(NUMBER_OF_PROJECTS)
  x2 = numpy.arange(MIN_X, MAX_X+1)

  y1 = numpy.log10(tuf_metadata_length)
  pyplot.plot(x1, y1, 'ro', label='TUF')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'r--')

  y1 = numpy.log10(tuf_version_metadata_length)
  pyplot.plot(x1, y1, 'ms', label='TUF-version')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'm--')

  y1 = numpy.log10(mercury_metadata_length)
  pyplot.plot(x1, y1, 'cx', label='Mercury-hash')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'c--')

  y1 = numpy.log10(mercury_nohash_metadata_length)

  pyplot.plot(x1, y1, 'g*', label='Mercury')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'g--')

  y1 = numpy.log10(mercury_project_metadata_length)
  pyplot.plot(x1, y1, 'b^', label='GPG/RSA')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'b--')

  # From /var/experiments-output/simple/compute-average-package-size.py
  AVG_PKG_SIZE = numpy.log10(659878)
  pyplot.hlines(AVG_PKG_SIZE, 0, MAX_X, colors='k', linestyles='-',
              label='Average downloaded package size')

  OBS_NUMBER_OF_PROJECTS = numpy.log2(NUMBER_OF_PROJECTS[-1])
  pyplot.vlines(OBS_NUMBER_OF_PROJECTS, MIN_Y, MAX_Y, colors='k',
                linestyles=':',
                label='Actual number of projects at end of month')

  pyplot.title('Initial cost as number of projects is varied')
  pyplot.legend(loc='upper left', fontsize=11)

  pyplot.xlabel('Number of projects', fontsize=14)
  xlabels = ['32', '64', '128', '256', '512', '1K', '2K', '4K', '8K', '16K',
             '32K', '64K', '128K', '256K', '512K', '1M']
  pyplot.xticks(x2, xlabels, fontsize=10)
  pyplot.xlim(MIN_X, MAX_X)

  pyplot.ylabel('Bandwidth cost', fontsize=14)
  yticks = numpy.arange(MIN_Y, MAX_Y+1)
  ylabels = ['100B', '1KB', '10KB', '100KB', '1MB', '10MB', '100MB']
  pyplot.yticks(yticks, ylabels, fontsize=14)
  pyplot.ylim(MIN_Y, MAX_Y)

  # write the actual plot
  VARY_COSTS_FOR_NEW_USERS_FILENAME = \
            os.path.join(METADATA_DIRECTORY, 'vary-number-of-new-projects.pdf')
  pyplot.savefig(VARY_COSTS_FOR_NEW_USERS_FILENAME)
  # clear figure
  pyplot.clf()


def plot_vary_frequency_of_project_creation_or_update():
  MIN_X, MAX_X = 0, 8
  MIN_Y, MAX_Y = 2, 9
  NUMBER_OF_FREQUENCIES = 9

  frequencies = [2**i for i in range(NUMBER_OF_FREQUENCIES)]

  mercury_project_metadata_length = []
  mercury_snapshot_metadata_length = []
  mercury_metadata_length = []

  mercury_nohash_project_metadata_length = []
  mercury_nohash_snapshot_metadata_length = []
  mercury_nohash_metadata_length = []

  tuf_version_project_metadata_length = []
  tuf_version_snapshot_metadata_length = []
  tuf_version_metadata_length = []

  tuf_project_metadata_length = []
  tuf_snapshot_metadata_length = []
  tuf_metadata_length = []

  # Over each frequency in increasing order...
  for f in frequencies:
    # INPUT
    if f==1.0: f=int(f)

    mercury_filename = os.path.join(METADATA_DIRECTORY,
                                    'mercury-best.f{}.json'.format(f))
    mercury_nohash_filename = os.path.join(METADATA_DIRECTORY,
                                           'mercury-nohash-best.f{}.json'.\
                                           format(f))
    tuf_version_filename = os.path.join(METADATA_DIRECTORY,
                                'tuf-version-best.f{}.json'.format(f))
    tuf_filename = os.path.join(METADATA_DIRECTORY,
                                'tuf-best.f{}.json'.format(f))

    # We care only about the recurring cost of a returning user.
    # Looks new, because the user had never been seen before in the log.
    mercury = read_json(mercury_filename)['new']
    mercury_nohash = read_json(mercury_nohash_filename)['new']
    tuf_version = read_json(tuf_version_filename)['new']
    tuf = read_json(tuf_filename)['new']
    assert mercury['package_length'] == mercury_nohash['package_length']
    assert mercury_nohash['package_length'] == tuf_version['package_length']
    assert tuf_version['package_length'] == tuf['package_length']

    # Draw the frequencies in reverse order for easier comprehension.
    mercury_snapshot_metadata_length.insert(0,
                                            mercury['snapshot_metadata_length'])

    mercury_project_metadata_length.insert(0,
                                           mercury['project_metadata_length'])

    mercury_nohash_snapshot_metadata_length.\
                           insert(0, mercury_nohash['snapshot_metadata_length'])

    mercury_nohash_project_metadata_length.\
                            insert(0, mercury_nohash['project_metadata_length'])

    tuf_version_snapshot_metadata_length.\
                              insert(0, tuf_version['snapshot_metadata_length'])

    tuf_version_project_metadata_length.\
                               insert(0, tuf_version['project_metadata_length'])

    tuf_snapshot_metadata_length.insert(0, tuf['snapshot_metadata_length'])

    tuf_project_metadata_length.insert(0, tuf['project_metadata_length'])

  assert len(mercury_project_metadata_length) == len(frequencies)
  assert len(mercury_snapshot_metadata_length) == len(frequencies)
  assert len(mercury_nohash_project_metadata_length) == len(frequencies)
  assert len(mercury_nohash_snapshot_metadata_length) == len(frequencies)
  assert len(tuf_version_project_metadata_length) == len(frequencies)
  assert len(tuf_version_snapshot_metadata_length) == len(frequencies)
  assert len(tuf_project_metadata_length) == len(frequencies)
  assert len(tuf_snapshot_metadata_length) == len(frequencies)

  # Produce tallies of metadata for each system.
  for i in range(len(frequencies)):
    mercury_total_length = mercury_snapshot_metadata_length[i] + \
                           mercury_project_metadata_length[i]
    mercury_metadata_length.append(mercury_total_length)

    mercury_nohash_total_length = mercury_nohash_snapshot_metadata_length[i] + \
                                  mercury_nohash_project_metadata_length[i]
    mercury_nohash_metadata_length.append(mercury_nohash_total_length)

    tuf_version_total_length = tuf_version_snapshot_metadata_length[i] + \
                               tuf_version_project_metadata_length[i]
    tuf_version_metadata_length.append(tuf_version_total_length)

    tuf_total_length = tuf_snapshot_metadata_length[i] + \
                       tuf_project_metadata_length[i]
    tuf_metadata_length.append(tuf_total_length)

  assert len(mercury_metadata_length) == len(mercury_nohash_metadata_length)
  assert len(mercury_nohash_metadata_length) == len(tuf_version_metadata_length)
  assert len(tuf_version_metadata_length) == len(tuf_metadata_length)

  # http://stackoverflow.com/a/30670983
  x1 = numpy.arange(MIN_X, MAX_X+1)
  x2 = numpy.arange(MIN_X, MAX_X+5)

  y1 = numpy.log10(tuf_metadata_length)
  pyplot.plot(x1, y1, 'ro', label='TUF')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'r--')

  y1 = numpy.log10(tuf_version_metadata_length)
  pyplot.plot(x1, y1, 'ms', label='TUF-version')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'm--')

  y1 = numpy.log10(mercury_metadata_length)
  pyplot.plot(x1, y1, 'cx', label='Mercury-hash')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'c--')

  y1 = numpy.log10(mercury_nohash_metadata_length)
  pyplot.plot(x1, y1, 'g*', label='Mercury')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'g--')

  print('GPG/RSA: {}'.format(mercury_project_metadata_length))
  y1 = numpy.log10(mercury_project_metadata_length)
  pyplot.plot(x1, y1, 'b^', label='GPG/RSA')
  m, c, *z = scipy.stats.linregress(x1, y1)
  y2 = m*x2+c
  pyplot.plot(x2, y2, 'b--')

  # From /var/experiments-output/simple/compute-average-package-size.py
  AVG_PKG_SIZE = numpy.log10(659878)
  pyplot.hlines(AVG_PKG_SIZE, MIN_X, MAX_X+4, colors='k', linestyles='solid',
                label='Average downloaded package size')

  pyplot.vlines(8, MIN_Y, MAX_Y, colors='k', linestyles=':',
                 label='Actual rate of updates over the month')

  pyplot.title('Recurring cost as rate of project updates is varied')
  pyplot.legend(loc='upper left', fontsize=11)

  pyplot.xlabel('The average number of projects updated per minute',
                fontsize=12)
  xlabels = ['$2^{-10}$', '$2^{-9}$', '$2^{-8}$', '$2^{-7}$',
             '$2^{-6}$', '$2^{-5}$', '$2^{-4}$', '$2^{-3}$', '$2^{-2}$',
             '$2^{-1}$', '$1$', '$2$', '$4$']
  pyplot.xticks(x2, xlabels, fontsize=14)
  pyplot.xlim(MIN_X, MAX_X+4)

  pyplot.ylabel('Bandwidth cost', fontsize=14)
  yticks = numpy.arange(MIN_Y, MAX_Y+1)
  ylabels = ['100B', '1KB', '10KB', '100KB', '1MB', '10MB', '100MB']
  pyplot.yticks(yticks, ylabels, fontsize=14)
  pyplot.ylim(MIN_Y, MAX_Y)

  # write the actual plot
  PLOT_FILENAME = os.path.join(METADATA_DIRECTORY,
                               'vary-rate-of-projects-created-or-updated.pdf')
  pyplot.savefig(PLOT_FILENAME)
  # clear figure
  pyplot.clf()


def read_json(json_filename, day_number=29):
  def sanity_check(results, key):
    assert key in results
    assert 'package_length' in results[key]
    assert 'project_metadata_length' in results[key]
    assert 'snapshot_metadata_length' in results[key]

  with open(json_filename) as json_file:
    day_number_str = str(day_number)
    results = json.load(json_file)[day_number_str]

  sanity_check(results, 'new')
  sanity_check(results, 'return')
  return results


if __name__ == '__main__':
  plot_vary_number_of_new_projects()
  plot_vary_frequency_of_project_creation_or_update()
