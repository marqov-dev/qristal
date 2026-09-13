"""Exact locked Core dependency-path guard transformation; no configure step."""
import hashlib

SOURCE_SHA256 = 'a1f682dcd200418ed36c584a86ed7b4733870b2c525d734f6673ba0440bfa76c'
OLD = b'''macro(is_in_install_path PATH RESULT)
  file(REAL_PATH ${CMAKE_INSTALL_PREFIX} INSTALL_DIR)
  file(REAL_PATH ${PATH} PACKAGE_DIR)
  string(FIND "${PACKAGE_DIR}" "${INSTALL_DIR}" POSITION)
  if (POSITION EQUAL 0)
    set(${RESULT} ON)
  else()
    set(${RESULT} OFF)
  endif()
endmacro()
'''
NEW = b'''macro(is_in_install_path PATH RESULT)
  set(${RESULT} OFF)
  if (NOT "${PATH}" STREQUAL "" AND NOT "${PATH}" MATCHES "(^|-)NOTFOUND$")
    file(REAL_PATH "${CMAKE_INSTALL_PREFIX}" INSTALL_DIR)
    file(REAL_PATH "${PATH}" PACKAGE_DIR)
    cmake_path(IS_PREFIX INSTALL_DIR "${PACKAGE_DIR}" NORMALIZE ${RESULT})
  endif()
endmacro()
'''
CALLS = (
    (b'is_in_install_path(${${arg_FIND_PACKAGE_NAME}_DIR} WAS_INSTALLED_BY_QRISTAL)',
     b'is_in_install_path("${${arg_FIND_PACKAGE_NAME}_DIR}" WAS_INSTALLED_BY_QRISTAL)'),
    (b'is_in_install_path(${${arg_FIND_PACKAGE_ADDITIONAL_RESULT_PATH_VAR}} WAS_INSTALLED_BY_QRISTAL)',
     b'is_in_install_path("${${arg_FIND_PACKAGE_ADDITIONAL_RESULT_PATH_VAR}}" WAS_INSTALLED_BY_QRISTAL)'),
)


def transform(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('unexpected locked dependency path source')
    for old, new in ((OLD, NEW), *CALLS):
        if data.count(old) != 1:
            raise ValueError('unexpected dependency path anchor')
        data = data.replace(old, new, 1)
    return data
