#!/usr/bin/env python3

# ----------------------------------------------------------------------------
# Copyright 2019 Drunella
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ----------------------------------------------------------------------------

import os
import sys
import glob
import subprocess
import argparse
import hashlib
import traceback
import pprint


def readblockmap_info(filename):
    directory = dict()
    with open(filename) as f:
        result = [line.split() for line in f]
        for l in result:
            directory[l[0]] = l[1:]
    return directory


def readdisks_info(filename):
    disks = []
    with open(filename) as f:
        result = [line.split() for line in f]
    #pprint.pprint(result)
    return result


def readdisks_getdiskinfo(disks, diskname):
    for d in disks:
        if d[0] == diskname:
            return d
    return []


def map_initialize():
    global bank_data, map_data
    map_data = bytearray([0xff] * 0x800)


def crtmap_appendentry(filename, block, name, address):
    with open(filename, "at") as f:
        content = "{0} f {1} addr 0x{2:04x}\n".format(block, name, address)
        return f.write(content)


def load_file(filename):
    with open(filename, "rb") as f:
        return f.read()


def write_prg(dirname, lowhigh, data):
    if lowhigh == 0:
        # low
        a = bytearray(2)
        a[0] = 0
        a[1] = 0x80
    elif lowhigh == 1:
        # high
        a = bytearray(2)
        a[0] = 0
        a[1] = 0xA0
    else:
        raise Exception("lowhigh can only be 0 or 1")
    
    with open(dirname, "wb") as f:
        #f.write(a)
        f.write(data)


def blockmap_appendentry(diskid, line, bank, highaddress):
    global map_data
    base = diskid * 256 + line * 2
    map_data[base] = bank
    map_data[base+1] = highaddress
    #print("blockmap_appendentry: " + str(base) + ": " + str(bank) + " " + str(highaddress))


def calculate_address(lowhigh):
    if lowhigh == 0:
        # low
        a = 0x80
    elif lowhigh == 1:
        # high
        a = 0xA0
    else:
        raise Exception("lowhigh can only be 0 or 1")
    return a


def main(argv):
    global bank_data, map_data
    p = argparse.ArgumentParser()
    p.add_argument("-v", dest="verbose", action="store_true", help="Verbose output.")
    p.add_argument("-o", dest="disks", action="store", required=True, help="disk configuration file.")
    p.add_argument("-f", dest="files", action="store", required=True, help="files directory.")
    p.add_argument("-m", dest="crtfile", action="store", required=True, help="crt.map file")
    p.add_argument("-d", dest="destination", action="store", required=True, help="destination directory.")
    p.add_argument("-b", dest="blockmap", action="store", required=True, help="blockmap file.")
    #p.add_argument("-f", dest="fileoutput", action="store", required=True, help="output data content file.")
    args = p.parse_args()
    #temp_path = os.path.join(args.build, "temp")
    #os.makedirs(temp_path, exist_ok=True)
    files_path = args.files #os.path.join(args.build, "files")
    os.makedirs(files_path, exist_ok=True)
    destination_path = args.destination #os.path.join(args.build, "obj")
    os.makedirs(destination_path, exist_ok=True)

    disks = readdisks_info(args.disks)
    blockmap = readblockmap_info(args.blockmap)

    map_initialize()
    if os.path.exists(args.crtfile):
        os.remove(args.crtfile)
    
    # add blocks file
    for d in ("britannia", "towne", "dwelling", "castle", "keep", "dungeon", "underworld"):
        diskinfo = readdisks_getdiskinfo(disks, d)
        starttrack = int(diskinfo[2], 0)
        height = int(diskinfo[4], 0) - int(diskinfo[2], 0) + 1
        diskid = int(diskinfo[1], 0) - 0x41
        startbank = int(blockmap[d][0], 0)
        lowhigh = int(blockmap[d][1], 0)
        block_data = load_file(os.path.join(files_path, d + ".data"))
        # build map and blocks
        map_data[diskid*256+255] = starttrack
        for b in range(0, height, 2):
            # double line or single line
            #factor = 2
            #if b+1 >= height:
            #    factor = 1

            # make data
            bank_data = bytearray([0xff] * 0x2000)
            baseaddress = calculate_address(lowhigh)
            
            if b+1 >= height:
                # one line
                s = b * 256*16
                l = 0x1000
                bank_data[0:l] = block_data[s:s+l]
                blockmap_appendentry(diskid, b, startbank, baseaddress)
            else:
                # two lines
                s = b * 256*16
                l = 0x2000
                bank_data[0:l] = block_data[s:s+l]
                blockmap_appendentry(diskid, b, startbank, baseaddress)
                blockmap_appendentry(diskid, b+1, startbank, baseaddress+0x10)

            # write data and map
            filename = "{0}_{1:02d}.aprg".format(d, b)
            write_prg(os.path.join(destination_path, filename), lowhigh, bank_data)
            crtmap_appendentry(args.crtfile, startbank, filename, baseaddress * 0x100)
            
            # increase values
            startbank += 1

    # write block map
    blockmap_bank = int(blockmap["blockmap"][0], 0)
    blockmap_lowhigh = int(blockmap["blockmap"][1], 0)
    blockmap_address = calculate_address(blockmap_lowhigh) * 256
    #blockmap_appendentry(0, b, startbank, baseaddress)
    blockmapname = os.path.join(destination_path, "blockmap.aprg")
    write_prg(blockmapname, blockmap_lowhigh, map_data)
    crtmap_appendentry(args.crtfile, blockmap_bank, "blockmap.aprg", blockmap_address)
    
    return 0

        
if __name__ == '__main__':
    try:
        retval = main(sys.argv)
        sys.exit(retval)
    except Exception as e:
        print(e)
        traceback.print_exc()
        sys.exit(1)
