CXX ?= g++
WIN_CXX ?= x86_64-w64-mingw32-g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra

.PHONY: all linux windows test clean

all: linux windows

build:
	mkdir -p build dist

linux: build
	$(CXX) $(CXXFLAGS) -Ivendor src/main.cpp -o build/TinyRoguesTracker-linux

windows: build
	$(WIN_CXX) $(CXXFLAGS) -static -Ivendor src/main.cpp -o dist/TinyRoguesTracker.exe
	test -f dist/TinyRoguesTracker.exe

report: linux
	./build/TinyRoguesTracker-linux --save fixtures/private/Public_Slot1_Save1.json --ids ids.json --report report.txt --no-pause

test: linux report
	python3 -m pytest -q

clean:
	rm -rf build dist report.txt
