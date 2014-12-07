#!/usr/bin/make -f

.PHONY: all build clean

all: build

clean:
	# clean i18n
	(cd po && $(MAKE) clean)

build:
	# build i18n
	(cd po && $(MAKE))
