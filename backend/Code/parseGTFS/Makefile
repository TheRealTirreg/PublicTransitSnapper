CXX = clang++ -Wall -Wextra -pedantic -std=c++2a
MAIN_BINARIES = $(basename $(wildcard *Main.cpp))
TEST_BINARIES = $(basename $(wildcard *Test.cpp))
HEADERS = $(wildcard *.h)
OBJECTS = $(addsuffix .o, $(basename $(filter-out %Main.cpp %Test.cpp, $(wildcard *.cpp))))
LIBRARIES = -lpthread -lm

.PRECIOUS: %.o
.SUFFIXES:
.PHONY: all compile test valgrind checkstyle clean install

all: compile test checkstyle

install: $(MAIN_BINARIES)

compile: $(MAIN_BINARIES) $(TEST_BINARIES)

test: $(TEST_BINARIES)
	for T in $(TEST_BINARIES); do ./$$T || exit; done

valgrind: $(TEST_BINARIES)
	for T in $(TEST_BINARIES); do valgrind --leak-check=full ./$$T; done

checkstyle:
	python3 cpplint.py --repository=. *.h *.cpp

clean:
	rm -f *.o
	rm -f $(MAIN_BINARIES)
	rm -f $(TEST_BINARIES)

%Main: %Main.o $(OBJECTS)
	$(CXX) -O -o $@ $^ $(LIBRARIES)

%Test: %Test.o $(OBJECTS)
	$(CXX) -o $@ $^ $(LIBRARIES) -lgtest -lgtest_main -lpthread

%.o: %.cpp $(HEADERS)
	$(CXX) -O -c $<