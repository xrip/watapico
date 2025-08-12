#!/usr/bin/env python3
"""
Watara Supervision ROM Header Generator
Reads .sv files from a directory and generates roms.h with ROM data arrays and RomEntry structs
"""

import os
import sys
import argparse
from pathlib import Path

def calculate_power_of_two_mask(size):
    """Calculate the next power of two mask for ROM size"""
    if size == 0:
        return 0x0000
    
    # Find next power of 2 that's >= size
    power = 1
    while power < size:
        power <<= 1
    
    return power - 1

def sanitize_name(filename):
    """Convert filename to valid C identifier"""
    # Remove extension and convert to valid C identifier
    name = Path(filename).stem
    # Replace invalid characters with underscores
    sanitized = ""
    for char in name:
        if char.isalnum() or char == '_':
            sanitized += char
        else:
            sanitized += '_'
    
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized
    
    # Limit to reasonable length for the struct (39 chars max for name field)
    return sanitized[:39]

def generate_rom_data_array(rom_data, var_name):
    """Generate C array declaration for ROM data"""
    lines = []
    lines.append(f"static const unsigned char __attribute__((section(\".watara_roms\"))) {var_name}[] = {{")
    
    # Format data in rows of 16 bytes
    for i in range(0, len(rom_data), 16):
        chunk = rom_data[i:i+16]
        hex_values = [f"0x{byte:02X}" for byte in chunk]
        line = "    " + ", ".join(hex_values)
        
        # Add comment with address only
        line += f",  // 0x{i:04X}"
        lines.append(line)
    
    # Remove trailing comma from last line
    if lines[-1].endswith(',  // 0x'):
        lines[-1] = lines[-1].replace(',  //', '   //')
    
    lines.append("};")
    return lines

def read_sv_files(directory):
    """Read all .sv files from directory and return list of ROM info"""
    roms = []
    sv_files = list(Path(directory).glob("*.sv"))
    
    if not sv_files:
        print(f"No .sv files found in directory: {directory}")
        return roms
    
    print(f"Found {len(sv_files)} .sv files")
    
    for sv_file in sorted(sv_files):
        try:
            with open(sv_file, 'rb') as f:
                rom_data = f.read()
            
            if len(rom_data) == 0:
                print(f"Warning: {sv_file.name} is empty, skipping")
                continue
            
            # Calculate mask
            mask = calculate_power_of_two_mask(len(rom_data))
            
            # Create ROM info
            rom_info = {
                'filename': sv_file.name,
                'sanitized_name': sanitize_name(sv_file.name),
                'data': rom_data,
                'size': len(rom_data),
                'mask': mask
            }
            
            roms.append(rom_info)
            print(f"  {sv_file.name}: {len(rom_data)} bytes, mask: 0x{mask:04X}")
            
        except Exception as e:
            print(f"Error reading {sv_file}: {e}")
    
    return roms

def generate_header_file(roms, output_file):
    """Generate the complete roms.h file"""
    lines = []
    
    # Header comments and includes
    lines.extend([
        "/*",
        " * roms.h - Watara Supervision ROM Data",
        " * Generated automatically - do not edit manually",
        f" * Contains {len(roms)} ROM(s)",
        " */",
        "",
        "#ifndef ROMS_H",
        "#define ROMS_H",
        "",
        "#ifdef __cplusplus",
        "extern \"C\" {",
        "#endif",
        "",
        "// ROM entry structure",
        "typedef struct {",
        "    unsigned int index;",
        "    char name[40];",
        "    unsigned int size;",
        "    unsigned int mask;",
        "    const unsigned char *data;",
        "} RomEntry;",
        "",
    ])
    
    # Generate data arrays for each ROM
    for rom in roms:
        lines.append(f"// ROM data for: {rom['filename']}")
        lines.extend(generate_rom_data_array(rom['data'], f"rom_data_{rom['sanitized_name']}"))
        lines.append("")
    
    # Generate ROM entries array
    lines.append("// ROM entries table")
    lines.append("static const RomEntry __attribute__((section(\".watara_rom_list\"))) rom_entries[] = {")
    
    for i, rom in enumerate(roms):
        # Remove .sv extension from display name
        display_name = Path(rom["filename"]).stem
        name_str = f'"{display_name}"'
        if len(name_str) > 41:  # Account for quotes (40 char field + quotes)
            name_str = f'"{display_name[:36]}..."'
        
        lines.append(f"    {{ {i:>3}, {name_str:<42}, {rom['size']:>8}, 0x{rom['mask']:04X}, rom_data_{rom['sanitized_name']} }},")
    
    lines.extend([
        "};",
        "",
        f"volatile uint16_t __attribute__((section(\".watara_roms_counter\"))) ROM_COUNT={len(roms)};",
        "",
        "// Helper functions",
        "static inline const RomEntry* get_rom_by_index(unsigned int index) {",
        "	return &rom_entries[index % ROM_COUNT];",
        "}",
        "",
        "#ifdef __cplusplus",
        "}",
        "#endif",
        "",
        "#endif // ROMS_H",
    ])
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))
        print(f"Generated {output_file} successfully")
        
        # Print summary
        total_size = sum(rom['size'] for rom in roms)
        print(f"Summary:")
        print(f"  Total ROMs: {len(roms)}")
        print(f"  Total size: {total_size:,} bytes ({total_size/1024:.1f} KB)")
        print(f"  Average size: {total_size//len(roms) if roms else 0:,} bytes")
        
    except Exception as e:
        print(f"Error writing {output_file}: {e}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Generate roms.h from Watara Supervision .sv ROM files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s roms/                    # Process all .sv files in roms/ directory
  %(prog)s roms/ -o includes/roms.h # Specify output file
  %(prog)s . --verbose              # Process current directory with verbose output
        """
    )
    
    parser.add_argument('directory', 
                        help='Directory containing .sv ROM files')
    parser.add_argument('-o', '--output', 
                        default='roms.h',
                        help='Output header file (default: roms.h)')
    parser.add_argument('-v', '--verbose', 
                        action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        sys.exit(1)
    
    # Read ROM files
    roms = read_sv_files(args.directory)
    
    if not roms:
        print("No valid .sv files found")
        sys.exit(1)
    
    # Generate header file
    if generate_header_file(roms, args.output):
        print(f"Success! Use #include \"{args.output}\" in your C code")
        if args.verbose:
            print("\nUsage example:")
            print("  const RomEntry* rom = get_rom_by_index(0);")
            print("  printf(\"ROM: %s, Size: %u, Data: %p\\n\", rom->name, rom->size, rom->data);")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()