#!/usr/bin/env bash
#set -x

# A few test on disk io performance using fio

# Environment variables

# Parameters to use
# FILESIZE=1G   # For testing only
FILESIZE=10G
BLOCKSIZE1=4k
BLOCKSIZE2=64k
BLOCKSIZE3=1M
# RUNTIME=15    # For testing only
RUNTIME=300
TMPFILE=tmp_test
TESTNAME=disk_test

# Store results according to this
BASEDIR=$(pwd)
OFNAME1=${BASEDIR}/bm_${BLOCKSIZE1}.txt
OFNAME2=${BASEDIR}/bm_${BLOCKSIZE2}.txt
OFNAME3=${BASEDIR}/bm_${BLOCKSIZE3}.txt


# Start with blocksize 4 KiB
# Random read
echo '==========================================================' > ${OFNAME1}
echo "Random read, Blocksize ${BLOCKSIZE1}" > ${OFNAME1}
fio --filename=${TMPFILE} --sync=1 --rw=randread --bs=${BLOCKSIZE1} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME1} && rm ${TMPFILE}

# Random write
echo '\n==========================================================' >> ${OFNAME1}
echo "Random write, Blocksize ${BLOCKSIZE1}" >> ${OFNAME1}
fio --filename=${TMPFILE} --sync=1 --rw=randwrite --bs=${BLOCKSIZE1} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME1} && rm ${TMPFILE}

# Sequential read
echo '\n==========================================================' >> ${OFNAME1}
echo "Sequential read, Blocksize ${BLOCKSIZE1}" > ${OFNAME1}
fio --filename=${TMPFILE} --sync=1 --rw=read --bs=${BLOCKSIZE1} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME1} && rm ${TMPFILE}

# Sequential write
echo '\n==========================================================' >> ${OFNAME1}
echo "Sequential write, Blocksize ${BLOCKSIZE1}" >> ${OFNAME1}
fio --filename=${TMPFILE} --sync=1 --rw=write --bs=${BLOCKSIZE1} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME1} && rm ${TMPFILE}


# Then blocksize 64 KiB
# Random read
echo '==========================================================' > ${OFNAME2}
echo "Random read, Blocksize ${BLOCKSIZE2}" > ${OFNAME2}
fio --filename=${TMPFILE} --sync=1 --rw=randread --bs=${BLOCKSIZE2} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME2} && rm ${TMPFILE}

# Random write
echo '\n==========================================================' >> ${OFNAME2}
echo "Random write, Blocksize ${BLOCKSIZE2}" >> ${OFNAME2}
fio --filename=${TMPFILE} --sync=1 --rw=randwrite --bs=${BLOCKSIZE2} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME2} && rm ${TMPFILE}

# Sequential read
echo '\n==========================================================' >> ${OFNAME2}
echo "Sequential read, Blocksize ${BLOCKSIZE2}" > ${OFNAME2}
fio --filename=${TMPFILE} --sync=1 --rw=read --bs=${BLOCKSIZE2} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME2} && rm ${TMPFILE}

# Sequential write
echo '\n==========================================================' >> ${OFNAME2}
echo "Sequential write, Blocksize ${BLOCKSIZE2}" >> ${OFNAME2}
fio --filename=${TMPFILE} --sync=1 --rw=write --bs=${BLOCKSIZE2} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME2} && rm ${TMPFILE}


# Finally blocksize 1 MiB
# Random read
echo '==========================================================' > ${OFNAME3}
echo "Random read, Blocksize ${BLOCKSIZE3}" > ${OFNAME3}
fio --filename=${TMPFILE} --sync=1 --rw=randread --bs=${BLOCKSIZE3} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME3} && rm ${TMPFILE}

# Random write
echo '\n==========================================================' >> ${OFNAME3}
echo "Random write, Blocksize ${BLOCKSIZE3}" >> ${OFNAME3}
fio --filename=${TMPFILE} --sync=1 --rw=randwrite --bs=${BLOCKSIZE3} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME3} && rm ${TMPFILE}

# Sequential read
echo '\n==========================================================' >> ${OFNAME3}
echo "Sequential read, Blocksize ${BLOCKSIZE3}" > ${OFNAME3}
fio --filename=${TMPFILE} --sync=1 --rw=read --bs=${BLOCKSIZE3} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME3} && rm ${TMPFILE}

# Sequential write
echo '\n==========================================================' >> ${OFNAME3}
echo "Sequential write, Blocksize ${BLOCKSIZE3}" >> ${OFNAME3}
fio --filename=${TMPFILE} --sync=1 --rw=write --bs=${BLOCKSIZE3} --numjobs=1 --iodepth=4 --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} >> ${OFNAME3} && rm ${TMPFILE}

