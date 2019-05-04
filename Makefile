# Settings
TARGET=c64
CL65=cl65
#CA65=ca65
#LD65=ld65
CL65FLAGS=-t $(TARGET) -I ./src/include
#CA65FLAGS=-t $(TARGET) -I . -I ./src/include --debug-info
#LD65FLAGS=

.SUFFIXES: .prg .s

# ultima 5
ultima5: build/u5remastered.crt

# all
all: build/obj/directory.data.prg build/obj/files.data.prg build/u5remastered.crt


# compile
%.o: %.s
	$(CA65) $(CA65FLAGS) -o $@ $<

# loader.prg
build/obj/loader.prg: src/ef/loader.s src/io/io.exported.inc
	$(CL65) $(CL65FLAGS) -o build/obj/loader.prg -C src/ef/loader.cfg src/ef/loader.s

# initialize
build/obj/initialize.prg: src/ef/initialize.s src/io/io.exported.inc
	$(CL65) $(CL65FLAGS) -o build/obj/initialize.prg -C src/ef/initialize.cfg src/ef/initialize.s

# data loader
build/obj/data_loader.prg src/io/data_loader.map: src/io/data_loader.s
	$(CL65) $(CL65FLAGS) -vm -m ./src/io/data_loader.map -o build/obj/data_loader.prg -C src/io/data_loader.cfg $^
# data loader map
src/io/data_loader.exported.inc: src/io/data_loader.map
	tools/parsemap.py -v -s ./src/io/data_loader.map -d ./src/io/data_loader.exported.inc -e get_crunched_byte -e load_prg -e save_prg_byte -e save_source_high -e save_source_low -e load_block -e load_destination_high -e load_destination_low -e save_source_low -e save_source_high

# io
build/obj/io.prg src/io/io.map: src/io/io.s src/io/data_loader.exported.inc
	$(CL65) $(CL65FLAGS) -vm -m ./src/io/io.map -o ./build/obj/io.prg -C ./src/io/io.cfg ./src/io/io.s
# io.map
src/io/io.exported.inc: src/io/io.map
	tools/parsemap.py -v -s ./src/io/io.map -d ./src/io/io.exported.inc -e IO_load_file_entry -e IO_read_block_entry -e IO_request_disk_id_entry -e IO_request_disk_char_entry -e IO_save_file_entry -e IO_read_block_alt_entry -e read_block_filename -e requested_disk -e save_files_flags
 
# exomizer
build/obj/exodecrunch.prg: src/exo/exodecrunch.s src/io/io.exported.inc
	$(CL65) $(CL65FLAGS) -vm -m $(<D)/exodecrunch.map -o $@ -C $(<D)/$(*F).cfg $<

# io jump table replacements
build/obj/temp.subs.patched.prg: src/io/io.exported.inc
	mkdir -p ./build/patches
	c1541 disks/osi.d64 -read temp.subs build/obj/temp.subs.prg
	tools/mkpatch_tempsubs.sh ./build/patches ./src/io/io.exported.inc
	tools/u5patch.py -v -s ./build/obj/temp.subs.prg -d ./build/obj/temp.subs.patched.prg ./build/patches/temp.subs.*

# raw files
build/files/files.list:
	mkdir -p ./build/files ./build/obj
	tools/extract.py -v -s ./disks -b ./build

# crunched
build/files/crunched.done: build/files/files.list
	tools/crunch.py -v -b ./build

# build efs
build/obj/directory.data.prg build/obj/files.data.prg: build/files/crunched.done
	tools/mkefs.py -v -s ./src -b ./build -e crunch

# build blocks
build/obj/crt.blocks.map: build/files/files.list
	tools/mkblocks.py -v -s src/ -b build/ -m build/obj/crt.blocks.map

# cartridge binary
build/obj/u5remastered.bin: build/obj/directory.data.prg build/obj/files.data.prg build/obj/exodecrunch.prg build/obj/initialize.prg build/obj/loader.prg src/ef/eapi-am29f040.prg build/obj/io.prg build/obj/data_loader.prg build/obj/exodecrunch.prg build/obj/temp.subs.patched.prg build/obj/crt.blocks.map
	cp ./src/crt.map ./build/obj/crt.map
	cp ./src/ef/eapi-am29f040.prg ./build/obj/eapi-am29f040.prg
	tools/mkbin.py -v -b ./build/ -m crt.map -m crt.blocks.map

# cartdridge crt
build/u5remastered.crt: build/obj/u5remastered.bin
	cartconv -t easy -o build/u5remastered.crt -i build/obj/u5remastered.bin -n "Ultima 5 Remastered Demo" -p

clean:
	rm -rf build/obj

mrproper:
	rm -rf build
	# all .o .map files
	rm src/ef/initialize.o
	rm src/ef/loader.o
	rm src/exo/exodecrunch.map
	rm src/exo/exodecrunch.o
	rm src/exo/exodecrunch.s.old
	rm src/io/data_loader.exported.inc
	rm src/io/data_loader.map
	rm src/io/data_loader.o
	rm src/io/io.exported.inc
	rm src/io/io.map
	rm src/io/io.o
