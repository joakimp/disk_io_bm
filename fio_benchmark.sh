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
OFNAME4="${BASEDIR}/bm_512k.txt"

# Flag parsing
SSD=false
HDD=false
CONCURRENCY=false
FULL=false
while getopts "shcf" opt; do
    case $opt in
        s) SSD=true ;;
        h) HDD=true ;;
        c) CONCURRENCY=true ;;
        f) FULL=true ;;
    esac
done
shift $((OPTIND-1))

# Set concurrency defaults
DEFAULT_JOBS=1
DEFAULT_IODEPTH=4
if [ "$CONCURRENCY" = true ]; then
    CONC_JOBS=4
    CONC_IODEPTH=16
else
    CONC_JOBS=1
    CONC_IODEPTH=4
fi

do_disk_test () {
	# Expected parameters: block size, outfile, type of test, append mode, latency mode, numjobs, iodepth
	# All other used variables are globally known.
	local BLOCKSIZE="$1"
	local OFNAME="$2"
	local TESTTYPE="$3"
	local APPEND="$4"
	local LATENCY="$5"
	local JOBS="$6"
	local IODEPTH="$7"

	# Parse TESTTYPE for rw and extra params
	local rw_part
	local extra
	if echo "$TESTTYPE" | grep -q ":"; then
		rw_part=$(echo "$TESTTYPE" | cut -d: -f1)
		extra=$(echo "$TESTTYPE" | cut -d: -f2)
	else
		rw_part="$TESTTYPE"
		extra=""
	fi

	if [ "$APPEND" = "true" ]; then
		echo "==========================================================" >> "${OFNAME}"
	else
		echo "==========================================================" > "${OFNAME}"
	fi
	echo ""  >> "${OFNAME}" # Print newline

	if [ "$APPEND" = "false" ]; then
		echo "Testing directory: ${BASEDIR}" >> "${OFNAME}"
	fi

	if [ "$rw_part" = "read" ] || [ "$rw_part" = "write" ]; then
		echo "This is sequential ${rw_part}, block size = ${BLOCKSIZE}" >> "${OFNAME}"
	else
		echo "This is ${rw_part}, block size = ${BLOCKSIZE}" >> "${OFNAME}"
	fi

	# Build lat option
	local lat_opt=""
	if [ "$LATENCY" = "true" ]; then
		lat_opt="--lat=1"
	fi

	fio --filename=${TMPFILE} --sync=1 --rw=$rw_part $extra --bs=${BLOCKSIZE} --numjobs=${JOBS} --iodepth=${IODEPTH} --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} --direct=1 $lat_opt >> "${OFNAME}" && rm ${TMPFILE}

}

summarize_results() {
    local summary_file="${BASEDIR}/summary.txt"
    echo "Generating summary..." >&2

    local data=()
    data+=("Test|IOPS Read|IOPS Write|BW Read|BW Write|Lat Avg Read (us)|Lat Avg Write (us)|CPU|Bar")

    local all_iops=()

    for file in "${BASEDIR}"/bm_*.txt; do
        [ -f "$file" ] || continue
        local basename=$(basename "$file" .txt)
        case "$basename" in
            bm_4k) tests=("randread 4k" "randwrite 4k" "read 4k" "write 4k") ;;
            bm_64k) tests=("randread 64k" "randwrite 64k" "read 64k" "write 64k") ;;
            bm_1M) tests=("randread 1M" "randwrite 1M" "read 1M" "write 1M") ;;
            bm_512k) tests=("randread 512k" "randwrite 512k" "read 512k" "write 512k") ;;
            bm_mixed) tests=("randrw 4k") ;;
            bm_trim) tests=("trim 4k") ;;
            *) continue ;;
        esac

        for test in "${tests[@]}"; do
            local test_type=${test% *}
            local block=${test#* }

            local read_iops="N/A"
            local write_iops="N/A"
            local read_bw="N/A"
            local write_bw="N/A"
            local read_lat="N/A"
            local write_lat="N/A"
            local cpu="N/A"

            if [ "$test_type" != "trim" ]; then
                read_iops=$(grep -A 30 "This is $test_type, block size = $block" "$file" | grep "read:" | grep -o "IOPS=[0-9]*" | head -1 | cut -d= -f2)
                write_iops=$(grep -A 30 "This is $test_type, block size = $block" "$file" | grep "write:" | grep -o "IOPS=[0-9]*" | head -1 | cut -d= -f2)
                read_bw=$(grep -A 30 "This is $test_type, block size = $block" "$file" | grep "read:" | grep -o "BW=[^)]*" | head -1 | cut -d= -f2)
                write_bw=$(grep -A 30 "This is $test_type, block size = $block" "$file" | grep "write:" | grep -o "BW=[^)]*" | head -1 | cut -d= -f2)
                read_lat=$(grep -A 30 "This is $test_type, block size = $block" "$file" | grep "read:" -A 10 | grep "avg=" | grep -o "avg=[0-9.]*" | head -1 | cut -d= -f2)
                write_lat=$(grep -A 30 "This is $test_type, block size = $block" "$file" | grep "write:" -A 10 | grep "avg=" | grep -o "avg=[0-9.]*" | head -1 | cut -d= -f2)
                cpu=$(grep -A 30 "This is $test_type, block size = $block" "$file" | grep "cpu" -A 1 | grep "usr=" | head -1 | sed 's/.*usr=\([0-9.]*%\), sys=\([0-9.]*%\).*/usr=\1 sys=\2/')
            fi

            [ -z "$read_iops" ] && read_iops="N/A"
            [ -z "$write_iops" ] && write_iops="N/A"
            [ -z "$read_bw" ] && read_bw="N/A"
            [ -z "$write_bw" ] && write_bw="N/A"
            [ -z "$read_lat" ] && read_lat="N/A"
            [ -z "$write_lat" ] && write_lat="N/A"
            [ -z "$cpu" ] && cpu="N/A"

            data+=("$test|$read_iops|$write_iops|$read_bw|$write_bw|$read_lat|$write_lat|$cpu|")

            # Collect IOPS for bars
            if [ "$read_iops" != "N/A" ]; then all_iops+=("$read_iops"); fi
            if [ "$write_iops" != "N/A" ]; then all_iops+=("$write_iops"); fi
        done
    done

    # Calculate bars
    local max_iops=0
    for iops in "${all_iops[@]}"; do
        if [ "$iops" -gt "$max_iops" ] 2>/dev/null; then max_iops=$iops; fi
    done

    if [ "$max_iops" -gt 0 ]; then
        local bar_length=20
        local i=1
        while [ $i -lt ${#data[@]} ]; do
            local line=${data[$i]}
            IFS='|' read -r test read_iops write_iops read_bw write_bw read_lat write_lat cpu bar <<< "$line"
            local bar_str=""
            if [ "$read_iops" != "N/A" ] && [ "$read_iops" -gt 0 ]; then
                local len=$(( read_iops * bar_length / max_iops ))
                bar_str=$(printf '%*s' "$len" '' | tr ' ' '#')
            fi
            if [ "$write_iops" != "N/A" ] && [ "$write_iops" -gt 0 ]; then
                local len=$(( write_iops * bar_length / max_iops ))
                bar_str="${bar_str}$(printf '%*s' "$len" '' | tr ' ' '*')"
            fi
            data[$i]="$test|$read_iops|$write_iops|$read_bw|$write_bw|$read_lat|$write_lat|$cpu|$bar_str"
            i=$((i+1))
        done
    fi

    # Output
    local table=$(printf '%s\n' "${data[@]}")
    if command -v column >/dev/null 2>&1; then
        table=$(echo "$table" | column -t -s '|')
    fi
    echo "$table"
    echo "$table" > "$summary_file"
    echo "Summary saved to $summary_file" >&2
}

# Do the test for block sizes 4 KiB, 64 KiB, and 1 MiB, respectively.
do_disk_test "4k" "${OFNAME1}" "randread" false true $DEFAULT_JOBS $DEFAULT_IODEPTH
do_disk_test "4k" "${OFNAME1}" "randwrite" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
do_disk_test "4k" "${OFNAME1}" "read" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
do_disk_test "4k" "${OFNAME1}" "write" true false $DEFAULT_JOBS $DEFAULT_IODEPTH

do_disk_test "64k" "${OFNAME2}" "randread" false false $CONC_JOBS $CONC_IODEPTH
do_disk_test "64k" "${OFNAME2}" "randwrite" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
do_disk_test "64k" "${OFNAME2}" "read" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
do_disk_test "64k" "${OFNAME2}" "write" true false $DEFAULT_JOBS $DEFAULT_IODEPTH

do_disk_test "1M" "${OFNAME3}" "randread" false false $DEFAULT_JOBS $DEFAULT_IODEPTH
do_disk_test "1M" "${OFNAME3}" "randwrite" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
do_disk_test "1M" "${OFNAME3}" "read" true true $DEFAULT_JOBS $DEFAULT_IODEPTH
do_disk_test "1M" "${OFNAME3}" "write" true false $DEFAULT_JOBS $DEFAULT_IODEPTH

# Lean additional tests
LEAN_RUNTIME=60
if [ "$FULL" = true ]; then LEAN_RUNTIME=300; fi

# Mixed RandRW
RUNTIME=$LEAN_RUNTIME
do_disk_test "4k" "${BASEDIR}/bm_mixed.txt" "randrw:rwmixread=70" false false $DEFAULT_JOBS $DEFAULT_IODEPTH

# Trim for SSD
if [ "$SSD" = true ]; then
    do_disk_test "4k" "${BASEDIR}/bm_trim.txt" "trim" false false $DEFAULT_JOBS $DEFAULT_IODEPTH
fi

# Full mode: additional 512k tests
if [ "$FULL" = true ]; then
    RUNTIME=300
    do_disk_test "512k" "${OFNAME4}" "randread" false false $DEFAULT_JOBS $DEFAULT_IODEPTH
    do_disk_test "512k" "${OFNAME4}" "randwrite" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
    do_disk_test "512k" "${OFNAME4}" "read" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
    do_disk_test "512k" "${OFNAME4}" "write" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
fi

# Generate summary
summarize_results

