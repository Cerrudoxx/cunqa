if(NOT DEFINED CUNQA_PYTHON_INSTALL_DIR)
    set(CUNQA_PYTHON_INSTALL_DIR "lib/python${Python_VERSION_MAJOR}.${Python_VERSION_MINOR}/site-packages/cunqa")
endif()

message(STATUS "Python modules will be installed to: ${CMAKE_INSTALL_PREFIX}/${CUNQA_PYTHON_INSTALL_DIR}")

add_subdirectory(circuit)

pybind11_add_module(qclient bindings.cpp)
target_link_libraries(qclient PRIVATE client) 

add_custom_command(TARGET qclient POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:qclient>
        "${CMAKE_CURRENT_SOURCE_DIR}"
)

install(TARGETS qclient DESTINATION "${CUNQA_PYTHON_INSTALL_DIR}")

configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/constants.py.in"
    "${CMAKE_CURRENT_BINARY_DIR}/constants.py"
    @ONLY
)

file(GLOB PYTHON_SCRIPTS "${CMAKE_CURRENT_SOURCE_DIR}/*.py")
install(FILES ${PYTHON_SCRIPTS} DESTINATION "${CUNQA_PYTHON_INSTALL_DIR}")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/constants.py" DESTINATION "${CUNQA_PYTHON_INSTALL_DIR}")

install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/qiskit_deps/noise_instructions.py" 
              "${CMAKE_CURRENT_SOURCE_DIR}/qiskit_deps/cunqabackend.py" 
        DESTINATION "${CUNQA_PYTHON_INSTALL_DIR}/qiskit_deps")
