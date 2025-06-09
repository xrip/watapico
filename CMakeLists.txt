cmake_minimum_required(VERSION 3.12)
set(PICO_FLASH_SIZE_BYTES 16777216)

set(CMAKE_C_STANDARD 11)
set(CMAKE_BUILD_TYPE "MinSizeRel")

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(watapico C CXX ASM)



set(OUTPUT_DIR "${CMAKE_SOURCE_DIR}/bin/${PICO_PLATFORM}/${CMAKE_BUILD_TYPE}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${OUTPUT_DIR}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${OUTPUT_DIR}")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${OUTPUT_DIR}")
pico_sdk_init()

add_compile_options(-flto -fwhole-program -ffunction-sections -fdata-sections -fms-extensions -Os)
add_link_options(-flto -fwhole-program)

add_executable(${PROJECT_NAME})

pico_define_boot_stage2(slower_boot ${PICO_DEFAULT_BOOT_STAGE2_FILE})
target_compile_definitions(slower_boot PRIVATE PICO_FLASH_SPI_CLKDIV=4)
pico_set_boot_stage2(${PROJECT_NAME} slower_boot)

pico_add_extra_outputs(${PROJECT_NAME})

target_compile_definitions(${PROJECT_NAME} PRIVATE
        PICO_PRINTF_ALWAYS_INCLUDED=0
        PICO_PANIC_FUNCTION=
)
pico_set_float_implementation(${PROJECT_NAME} none) # size optimizations
pico_set_double_implementation(${PROJECT_NAME} none) # size optimizations
pico_set_printf_implementation(${PROJECT_NAME} none)

target_sources(${PROJECT_NAME} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/watapico.c)

target_link_libraries(${PROJECT_NAME}
        pico_runtime
        -Wl,--wrap=atexit # size optimizations
)
target_link_options(${PROJECT_NAME} PRIVATE -Xlinker --print-memory-usage --data-sections --function-sections)