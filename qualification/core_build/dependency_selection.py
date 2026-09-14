"""Scoped source override selection after the exact dependency-path guard."""
import hashlib

SOURCE_SHA256 = '37480e0849a7cb4865ae3189213c67e979696853f98b723e8e1db46d29530502'
OLD = b'''  if (arg_FIND_PACKAGE_VERSION)
    if(${arg_FIND_PACKAGE_VERSION} STREQUAL " ")
      find_package(${arg_FIND_PACKAGE_NAME} QUIET ${arg_FIND_PACKAGE_ARGUMENTS})
    else()
      find_package(${arg_FIND_PACKAGE_NAME} ${arg_FIND_PACKAGE_VERSION} QUIET ${arg_FIND_PACKAGE_ARGUMENTS})
    endif()
  else()
    find_package(${arg_FIND_PACKAGE_NAME} ${VERSION} QUIET ${arg_FIND_PACKAGE_ARGUMENTS})
  endif()
'''
NEW = b'''  if (DEFINED CPM_${NAME}_SOURCE AND NOT "${CPM_${NAME}_SOURCE}" STREQUAL "")
    # Honor the explicit source override without disabling nested required lookup.
    set(${arg_FIND_PACKAGE_NAME}_FOUND FALSE)
  else()
''' + b''.join(b'  ' + line for line in OLD.splitlines(keepends=True)) + b'''  endif()
'''


def transform(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256 or data.count(OLD) != 1:
        raise ValueError('unexpected dependency selection source')
    return data.replace(OLD, NEW, 1)
