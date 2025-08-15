# RP2040-based Watara Supervision Flash Cartridge

![image](https://github.com/user-attachments/assets/b708a552-b319-4aea-887f-9cbb1108649a)

## Overview

This project implements a flash cartridge for the Watara Supervision handheld game console using a Raspberry Pi Pico (RP2040). It lets you load and play Watara Supervision ROM files (`.sv`) on original hardware by serving ROM data from the RP2040 to the console bus.

Watara menu rom from https://github.com/vrodin/menu-watara

## Web-based ROM Manager

Download the latest firmware: [Watapico Firmware](https://github.com/xrip/watapico/releases/latest/download/watapico.uf2)

A web-based ROM manager is available to simplify the process of adding and removing ROMs from the firmware. You can access it here: [Watapico ROM Manager](https://xrip.github.io/watapico/rom_manager.html) 


### How to use the ROM Manager

1.  **Open the [Watapico ROM Manager](https://xrip.github.io/watapico/rom_manager.html)** in your web browser.
2.  **Load your `watapico.uf2` firmware file** by dragging and dropping it into the designated area or by clicking to select it.
3.  **Manage your ROMs:**
    *   The current ROMs will be displayed in a list.
    *   You can delete ROMs by clicking the "Delete" button next to them.
    *   You can add new `.sv` ROMs by dragging and dropping them into the ROMs area.
4.  **Save your changes:**
    *   Click the "Save Updated UF2 File" button to generate and download a new `watapico_updated.uf2` file with your changes.


## Hardware

- Download the manufacturing files: [Gerbers](https://github.com/xrip/watapico/raw/refs/heads/master/watara-cartridge-gerber.zip) or the full [KiCad project](https://github.com/xrip/watapico/raw/refs/heads/master/WatapicoCartrigeProject.zip).
- Use a RP2040 board that exposes GPIO 0–29. The common purple RP2040 clone that breaks out all 30 GPIOs is recommended.

### RP2040 pin mapping

The firmware assumes the following fixed wiring between the RP2040 and the Supervision cartridge connector:

| Bus signal | RP2040 GPIO |
| --- | --- |
| Address A0–A16 | GP0–GP16 |
| Data D0–D7 | GP17–GP24 |
| PWR_ON | GP25 |
| /RD | GP29 |

Notes:
- System clock is set to 400 MHz for timing headroom.
- `PWR_ON` is driven high to simulate cartridge presence/power.

## Software/Firmware

The project has two main components:

- Firmware (`watapico.c`): Initializes clocks and GPIOs and serves data during /RD cycles. On boot it selects a ROM at random and mirrors it onto the data bus.
- ROM tool (`roms/makeroms.py`): Converts `.sv` files into a generated header (`roms/roms.h`) containing ROM byte arrays and a lookup table.

### ROM format, selection, and limits

- Supported input: Watara Supervision `.sv` files.
- On boot, the firmware selects the next ROM using a persistent index stored at the end of flash. The index is incremented and saved on each start, so each power cycle advances to the next ROM.
- Address wrap: the generator computes a power-of-two mask so smaller ROMs mirror correctly over the address space.
- Important: The firmware buffer is 64 KiB (`uint8_t rom[65536]`). Do not include ROMs larger than 64 KiB or they will not fit.

## Directory structure

- `watapico.c`: Main RP2040 firmware.
- `CMakeLists.txt`: Build configuration (Pico SDK; MinSizeRel by default).
- `roms/`: Place your `.sv` files here and store the generated header here.
  - `roms/makeroms.py`: ROM header generator.
  - `roms/roms.h`: Generated. Do not edit manually.

## Usage

The recommended way to manage ROMs is to use the [web-based ROM manager](#web-based-rom-manager).

However, if you prefer to use the command-line tools, you can follow these steps:

### 1) Add ROMs and generate header

1. Copy your `.sv` files into `roms/`.
2. Generate the header (ensure the output path matches the include in `watapico.c`):

   ```bash
   python3 roms/makeroms.py roms/ -o roms/roms.h
   ```

### 2) Build the firmware

Prerequisites:
- Install the Raspberry Pi Pico SDK and toolchain, and set `PICO_SDK_PATH`.

Configure and build:

```bash
export PICO_SDK_PATH=/path/to/pico-sdk
cmake -S . -B build -DPICO_PLATFORM=pico
cmake --build build -j
```

Artifacts are written under `bin/<platform>/<config>/`. With defaults this is:

- `bin/pico/MinSizeRel/watapico.uf2`

### 3) Flash to the Pico

1. Hold BOOTSEL and plug the Pico into USB.
2. Copy `watapico.uf2` to the mass-storage device.

## Contributing

Contributions are welcome! Please open an issue or PR.

## Credits

+ Hardware design: Sa Gin
+ Software: xrip, [vrodin](https://github.com/vrodin)
+ Beta testing: Oleg

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
