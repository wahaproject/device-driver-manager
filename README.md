Device Driver Manager

Currently Nvidia, ATI, Intel, VIA and Broadcom are supported.
It also checks whether or not the PAE kernel can be installed on multi-processor 32-bit systems.

DDM uses the repositories to download and install the appropriate packages.

Debug run: ddm -d
This will generate a log file: $HOME/ddm.log