"""Bounded Eigen child configure/install handling after binary-directory staging."""
import hashlib

SOURCE_SHA256 = '342cc2bcf56d5c90944cc4e332d20e70f258e72e6f27a258778f7080408d93b1'
OLD = b'''    execute_process(COMMAND ${CMAKE_COMMAND} ${Eigen3_SOURCE_DIR} -DCMAKE_INSTALL_PREFIX=${Eigen3_INSTALL_DIR} WORKING_DIRECTORY ${Eigen3_BINARY_DIR})
    execute_process(COMMAND ${CMAKE_COMMAND} --install ${Eigen3_BINARY_DIR})
    execute_process(COMMAND ${CMAKE_COMMAND} -E rm -rf ${Eigen3_BINARY_DIR})
'''
NEW = b'''    execute_process(
      COMMAND "${CMAKE_COMMAND}" -S "${Eigen3_SOURCE_DIR}" -B "${Eigen3_BINARY_DIR}"
              "-DCMAKE_INSTALL_PREFIX=${Eigen3_INSTALL_DIR}" -DBUILD_TESTING=OFF -DEIGEN_BUILD_TESTING=OFF -DEIGEN_BUILD_DOC=OFF
      RESULT_VARIABLE EIGEN_CONFIGURE_RESULT
    )
    if(NOT EIGEN_CONFIGURE_RESULT STREQUAL "0")
      message(FATAL_ERROR "Eigen configure failed: ${EIGEN_CONFIGURE_RESULT}")
    endif()
    execute_process(
      COMMAND "${CMAKE_COMMAND}" --install "${Eigen3_BINARY_DIR}"
      RESULT_VARIABLE EIGEN_INSTALL_RESULT
    )
    if(NOT EIGEN_INSTALL_RESULT STREQUAL "0")
      message(FATAL_ERROR "Eigen install failed: ${EIGEN_INSTALL_RESULT}")
    endif()
'''


def transform(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256 or data.count(OLD) != 1:
        raise ValueError('unexpected Eigen configure source')
    return data.replace(OLD, NEW, 1)
