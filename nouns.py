'''
Some common names for, like, common things.
'''


# 1st-party
import os


LOG_FORMAT = '[%(asctime)s UTC] [%(levelname)s] '\
             '[%(filename)s:%(funcName)s:%(lineno)s] %(message)s'

PYPI_DIRECTORY = '/var/pypi.python.org/web'
SIMPLE_DIRECTORY = os.path.join(PYPI_DIRECTORY, 'simple')
PACKAGES_DIRECTORY = os.path.join(PYPI_DIRECTORY, 'packages')

EXPERIMENTS_OUTPUT_DIRECTORY = '/var/experiments-output/'
REQUESTS_FILENAME = os.path.join(EXPERIMENTS_OUTPUT_DIRECTORY,
                                 'simple/sorted.mercury.log.new')
METADATA_DIRECTORY = os.path.join(EXPERIMENTS_OUTPUT_DIRECTORY, 'metadata')

# Frequency f > 0 of project creation or update.
# Set f < 1 to speed up snapshots, f=1 to run them in realtime, and f > 1 to
# slow them down.
FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE = 2**0

# Amount of time to limit reading of metadata as well as processing package
# requests. Useful to limit amount of working memory. Use a falsy value
# (e.g. None) to set no limit.
#TIME_LIMIT_IN_SECONDS = 1655
TIME_LIMIT_IN_SECONDS = None

# Mercury
MERCURY_DIRTY_PROJECTS_CACHE_FILEPATH = \
          os.path.join(METADATA_DIRECTORY, 'MERCURY-DIRTY-PROJECTS-CACHE.json')
MERCURY_METADATA_PATCH_LENGTH_CACHE_FILEPATH = \
    os.path.join(METADATA_DIRECTORY, 'MERCURY-METADATA-PATCH-LENGTH-CACHE.json')

MERCURY_BEST_LOG_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'read-mercury-metadata-best.f{}.log'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))
MERCURY_WORST_LOG_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'read-mercury-metadata-worst.f{}.log'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

MERCURY_BEST_OUTPUT_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'mercury-best.f{}.json'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))
MERCURY_WORST_OUTPUT_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'mercury-worst.f{}.json'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

MERCURY_DIRECTORY = os.path.join(METADATA_DIRECTORY, 'mercury/')

# Mercury-nohash
MERCURY_NOHASH_DIRTY_PROJECTS_CACHE_FILEPATH = \
    os.path.join(METADATA_DIRECTORY, 'MERCURY-NOHASH-DIRTY-PROJECTS-CACHE.json')
MERCURY_NOHASH_METADATA_PATCH_LENGTH_CACHE_FILEPATH = \
                 os.path.join(METADATA_DIRECTORY,
                              'MERCURY-NOHASH-METADATA-PATCH-LENGTH-CACHE.json')

MERCURY_NOHASH_BEST_LOG_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'read-mercury-nohash-metadata-best.f{}.log'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))
MERCURY_NOHASH_WORST_LOG_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'read-mercury-nohash-metadata-worst.f{}.log'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

MERCURY_NOHASH_BEST_OUTPUT_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'mercury-nohash-best.f{}.json'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))
MERCURY_NOHASH_WORST_OUTPUT_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'mercury-nohash-worst.f{}.json'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

MERCURY_NOHASH_DIRECTORY = os.path.join(METADATA_DIRECTORY, 'mercury-nohash/')

# TUF
TUF_DIRTY_PROJECTS_CACHE_FILEPATH = \
              os.path.join(METADATA_DIRECTORY, 'TUF-DIRTY-PROJECTS-CACHE.json')
TUF_METADATA_PATCH_LENGTH_CACHE_FILEPATH = \
        os.path.join(METADATA_DIRECTORY, 'TUF-METADATA-PATCH-LENGTH-CACHE.json')

TUF_COST_FOR_NEW_USERS_FILEPATH = \
                os.path.join(METADATA_DIRECTORY, 'TUF-COST-FOR-NEW-USERS.json')

TUF_BEST_LOG_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'read-tuf-metadata-best.f{}.log'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

TUF_WORST_LOG_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'read-tuf-metadata-worst.f{}.log'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

TUF_BEST_OUTPUT_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'tuf-best.f{}.json'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

TUF_WORST_OUTPUT_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'tuf-worst.f{}.json'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

TUF_DIRECTORY = os.path.join(METADATA_DIRECTORY, 'tuf/')

# TUF-version
TUF_VERSION_COST_FOR_NEW_USERS_FILEPATH = \
         os.path.join(METADATA_DIRECTORY, 'TUF-VERSION-COST-FOR-NEW-USERS.json')

TUF_VERSION_BEST_LOG_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'read-tuf-version-metadata-best.f{}.log'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

TUF_VERSION_WORST_LOG_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'read-tuf-version-metadata-worst.f{}.log'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

TUF_VERSION_BEST_OUTPUT_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'tuf-version-best.f{}.json'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))

TUF_VERSION_WORST_OUTPUT_FILENAME = \
                  os.path.join(METADATA_DIRECTORY,
                               'tuf-version-worst.f{}.json'\
                               .format(FREQUENCY_OF_PROJECT_CREATION_OR_UPDATE))
