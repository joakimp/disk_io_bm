#!/usr/bin/env bash
#set -x

# A few test on disk io performance using fio

# Environment variables

# Parameters to use
# FILESIZE=1G   # For testing only
FILESIZE=10G

# RUNTIME=15    # For testing only
RUNTIME=300
TMPFILE=tmp_test
TESTNAME=disk_test

# Store results according to this
BASEDIR="$(pwd)"
OFNAME1="${BASEDIR}/bm_4k.txt"
OFNAME2="${BASEDIR}/bm_64k.txt"
OFNAME3="${BASEDIR}/bm_1M.txt"


do_disk_test () { 
	# Expected parameters: block size, outfile, type of test, append mode (or not)
	# All other used variables are globally known.
	# Local names to use for clarity ($0 refers to the function name), derivied from argument list
	local BLOCKSIZE="$1"
	local OFNAME="$2"
	local TESTTYPE="$3"
	local APPEND="$4"
	
	if [ "$APPEND" = "true" ]; then
		echo "==========================================================" >> "${OFNAME}"
	else
		echo "==========================================================" > "${OFNAME}"
	fi	
	echo ""  >> "${OFNAME}" # Print newline
		
	if [ "${TESTTYPE}" = "read" ] || [ "${TESTTYPE}" = "write" ]; then
		echo "This is sequential ${TESTTYPE}, block size = ${BLOCKSIZE}" >> "${OFNAME}"		
	else
		echo "This is ${TESTTYPE}, block size = ${BLOCKSIZE}" >> "${OFNAME}"
	fi
	
	fio --filename=${TMPFILE} --sync=1 --rw=$TESTTYPE --bs=${BLOCKSIZE} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> "${OFNAME}" && rm ${TMPFILE}
	
}


# Do the test for block sizes 4 KiB, 64 KiB, and 1 MiB, respectively.
do_disk_test "4k" "${OFNAME1}" "randread" false
do_disk_test "4k" "${OFNAME1}" "randwrite" true
do_disk_test "4k" "${OFNAME1}" "read" true
do_disk_test "4k" "${OFNAME1}" "write" true

do_disk_test "64k" "${OFNAME2}" "randread" false
do_disk_test "64k" "${OFNAME2}" "randwrite" true
do_disk_test "64k" "${OFNAME2}" "read" true
do_disk_test "64k" "${OFNAME2}" "write" true

do_disk_test "1M" "${OFNAME3}" "randread" false
do_disk_test "1M" "${OFNAME3}" "randwrite" true
do_disk_test "1M" "${OFNAME3}" "read" true
do_disk_test "1M" "${OFNAME3}" "write" true


