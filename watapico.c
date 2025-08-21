#include <string.h>

#include <pico/runtime.h>

#include <hardware/gpio.h>
#include <hardware/clocks.h>
#include <hardware/flash.h>
#include <hardware/sync.h>
#include <hardware/structs/vreg_and_chip_reset.h>

#include "./roms/roms.h"

// Address Bus (A0 - A16)
#define ADDR_MASK  0x1FFFF  // Bits 0-16

// Data Bus (D0 - D7)
#define DATA_MASK  (0xFF << 17)

// /RD
#define RD_PIN 29
#define READ_MASK (1u << RD_PIN)

#define PWR_ON_PIN 25
#define PWR_ON_MASK (1u << PWR_ON_PIN)

uint8_t __aligned(4096) rom[65536];
uint32_t ROM_MASK = 0xFFFF;

#define MENU_ROM 0

// -----------------------------------------------------------------------------
// Flash-backed ROM index storage (at end of external flash)
// -----------------------------------------------------------------------------

#ifndef PICO_FLASH_SIZE_BYTES
#error PICO_FLASH_SIZE_BYTES must be defined by the build system
#endif

#define SETTINGS_SECTOR_SIZE   4096u
#define SETTINGS_PAGE_SIZE      256u
#define SETTINGS_MAGIC   0x57544150u /* "WTAP" */

// Place settings in the last 4 KiB sector of flash
#define SETTINGS_FLASH_OFFSET  (PICO_FLASH_SIZE_BYTES - SETTINGS_SECTOR_SIZE)
#define SETTINGS_XIP_ADDR      (XIP_BASE + SETTINGS_FLASH_OFFSET)

typedef struct {
    uint32_t magic;
    uint32_t rom_index;
    uint8_t reserved[SETTINGS_PAGE_SIZE - 8];
} __attribute__((packed)) Settings;


__always_inline static const Settings *get_settings_xip_ptr() {
    return (const Settings *) SETTINGS_XIP_ADDR;
}

__always_inline static uint32_t load_rom_index_from_flash() {
    const Settings *page = get_settings_xip_ptr();
    if (page->magic == SETTINGS_MAGIC && page->rom_index < ROM_COUNT) {
        return page->rom_index;
    }
    return 0; // default on first boot or uninitialized flash
}

__always_inline static void save_rom_index_to_flash(const uint32_t rom_index) {
    const Settings settings = {
        .magic = SETTINGS_MAGIC,
        .rom_index = rom_index
    };

    const uint32_t interrupts = save_and_disable_interrupts();
    flash_range_erase(SETTINGS_FLASH_OFFSET, SETTINGS_SECTOR_SIZE);
    flash_range_program(SETTINGS_FLASH_OFFSET, (const uint8_t *)&settings, 8);
    restore_interrupts(interrupts);
}

uint32_t current_rom;

__always_inline static void handle_bus() {
    while (true) {
        while (gpio_get_all() & READ_MASK) {}

        const uint32_t address = gpio_get_all() & ROM_MASK;

        gpio_set_dir_out_masked(DATA_MASK);
        gpio_put_all(rom[address] << 17 | PWR_ON_MASK);
        gpio_set_dir_in_masked(DATA_MASK);

        if (MENU_ROM == current_rom && address >= 0x1000 && address <= 0x10FF) {
            current_rom = address & 0xFF;
            const RomEntry *rom_entry = get_rom_by_index(current_rom);
            memcpy(rom, rom_entry->data, rom_entry->size);
            ROM_MASK = rom_entry->mask;
            save_rom_index_to_flash(current_rom);
        }
    }
}

int __time_critical_func(main) () {
    // Set the system clock speed.
    hw_set_bits(&vreg_and_chip_reset_hw->vreg, VREG_AND_CHIP_RESET_VREG_VSEL_BITS);
    set_sys_clock_hz(400 * MHZ, true); // 100x of Watara Supervision clock speed

    // Initialize all input pins at once
    gpio_init_mask(ADDR_MASK | DATA_MASK | READ_MASK | PWR_ON_MASK);
    gpio_set_dir_in_masked(ADDR_MASK | DATA_MASK | READ_MASK);

    // Load persistent ROM index from the last flash sector
    current_rom = load_rom_index_from_flash();

    const RomEntry *rom_entry = get_rom_by_index(current_rom);
    memcpy(rom, rom_entry->data, rom_entry->size);

    if (MENU_ROM == current_rom) {
        rom[0x1100] = ROM_COUNT - 1;
        memcpy(&rom[0x1101], rom_entries, sizeof(RomEntry) * ROM_COUNT);
    }

    ROM_MASK = rom_entry->mask;

    // Increment and persist the ROM index for next boot
    save_rom_index_to_flash(0);

    gpio_set_dir(PWR_ON_PIN, GPIO_OUT);
    gpio_put(PWR_ON_PIN, 1);

    handle_bus();
}
