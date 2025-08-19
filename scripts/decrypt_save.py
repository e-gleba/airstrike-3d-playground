#!/usr/bin/env python3
import sys
import struct

def xor_decrypt(data, key):
    decrypted = bytearray()
    key_len = len(key)
    
    for i, byte in enumerate(data):
        key_index = i % key_len
        decrypted.append(byte ^ key[key_index])
    
    return bytes(decrypted)

def parse_file(path):
    try:
        with open(path, 'rb') as f:
            # read entire header (0x108 bytes)
            header = f.read(0x108)
            if len(header) != 0x108:
                return False
            
            print(f"full header ({len(header)} bytes): {header.hex()}")
            
            # extract key from header (starts at offset 4, length 0x100)
            key = header[4:4+0x100]
            print(f"key ({len(key)} bytes): {key.hex()}")
            
            # read encrypted data (0x574 bytes according to save function)
            data = f.read(0x574)
            if not data:
                print("no data found")
                return True
                
            print(f"encrypted data ({len(data)} bytes): {data.hex()}")
            
            # decrypt data
            decrypted = xor_decrypt(data, key)
            print(f"decrypted ({len(decrypted)} bytes): {decrypted.hex()}")
            
            try:
                text = decrypted.decode('utf-8', errors='replace')
                print(f"decrypted text: {text}")
            except:
                # try other encodings
                for encoding in ['latin1', 'cp1252']:
                    try:
                        text = decrypted.decode(encoding, errors='replace')
                        print(f"decrypted text ({encoding}): {text}")
                        break
                    except:
                        continue
                else:
                    print("decrypted text: <binary data>")
            
        return True
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: parse_file.py <file>", file=sys.stderr)
        sys.exit(1)
    
    if not parse_file(sys.argv[1]):
        sys.exit(1)

