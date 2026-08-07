CXX ?= g++
WIN_CXX ?= x86_64-w64-mingw32-g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra

.PHONY: all linux windows report test package clean

all: linux windows

build:
	mkdir -p build dist

linux: build
	$(CXX) $(CXXFLAGS) -Ivendor src/main.cpp -o build/TinyRoguesTracker-linux

windows: build
	$(WIN_CXX) $(CXXFLAGS) -static -Ivendor src/main.cpp -o dist/TinyRoguesTracker.exe
	test -f dist/TinyRoguesTracker.exe

report: linux
	./build/TinyRoguesTracker-linux --save fixtures/sample_save.json --ids ids.json --report report.txt --csv report.csv --character 21 --no-pause

test: linux report
	python3 -m pytest -q

package: all report
	rm -rf dist/package dist/TinyRoguesTracker-v2-windows.zip
	mkdir -p dist/package
	cp dist/TinyRoguesTracker.exe ids.json README.md report.txt report.csv dist/package/
	python3 scripts/package_windows.py

clean:
	rm -rf build dist report.txt report.csv
