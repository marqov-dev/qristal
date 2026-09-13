"""Exact-version transformation for the locked Core export, not arbitrary sources."""
import hashlib

SOURCE_SHA256 = '7f9ee9ef437b81471fbb01450fd7f099b1e6af19700d3dd34ee6ebb2cb6740db'
OLD = b'# Get version number from git tag. Must be done before the project command is called.\nfind_package(Git)\nif(GIT_FOUND)\n  execute_process(\n    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}\n    COMMAND git describe --tags --abbrev=0\n    OUTPUT_VARIABLE PROJECT_VERSION\n    OUTPUT_STRIP_TRAILING_WHITESPACE\n    RESULT_VARIABLE GIT_DESCRIBE_RESULT\n  )\n\n  if (NOT GIT_DESCRIBE_RESULT EQUAL 0)\n    message(FATAL_ERROR "Failed to get git tag: git describe returned ${GIT_DESCRIBE_RESULT}")\n  endif()\n\n  string(REGEX REPLACE "^v(.*)" "\\\\1" PROJECT_VERSION "${PROJECT_VERSION}")\nendif()\n\n'
NEW = b'# Version of the exact locked public source export (v1.8.1).\n# Git metadata is intentionally absent from verified build inputs.\nfind_package(Git)\nset(PROJECT_VERSION "1.8.1")\n\n'

def transform(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256 or data.count(OLD) != 1:
        raise ValueError('unexpected Core version source')
    return data.replace(OLD, NEW, 1)
