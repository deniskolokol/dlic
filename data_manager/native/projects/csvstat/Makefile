CXX=g++
CXX_FLAGS=-std=c++0x -O3
SOURCE=main.cpp Jzon.cpp
BIN_FILE=../../bin/csvstat
INCLUDE_FLAGS=-I../../include
LIB_FLAGS=-lboost_system -lboost_filesystem -lboost_iostreams -lz -lhdf5

all: $(BIN_FILE)

$(BIN_FILE): $(SOURCE)
	mkdir -p ../../bin
	$(CXX) $(CXX_FLAGS) $(INCLUDE_FLAGS) $(SOURCE) -o$(BIN_FILE) $(LIB_FLAGS)

clean:
	rm -f *.o
	rm -f ${BIN_FILE}

install: $(BIN_FILE)
	cp $(BIN_FILE) /usr/local/bin