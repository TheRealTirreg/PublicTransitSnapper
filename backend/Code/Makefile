TEST_CMD = python3 -m doctest
# set max line line length to 120, like in PyCharm
CHECKSTYLE_CMD = flake8 --max-line-length=120

all: compile test checkstyle

compile:
	@echo "Nothing to compile for Python"

test:
	$(TEST_CMD) *.py

checkstyle:
	$(CHECKSTYLE_CMD) *.py

clean:
	rm -f *.pyc
	rm -rf __pycache__
