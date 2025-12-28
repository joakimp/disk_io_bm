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

# Clean previous output files
rm -f "${BASEDIR}"/bm_*.txt "${BASEDIR}"/summary.txt

# Store results according to this
BASEDIR="$(pwd)"
OFNAME1="${BASEDIR}/bm_4k.txt"
OFNAME2="${BASEDIR}/bm_64k.txt"
OFNAME3="${BASEDIR}/bm_1M.txt"
OFNAME4="${BASEDIR}/bm_512k.txt"

# Flag parsing (support both short and long options)
SSD=false
HDD=false
CONCURRENCY=false
FULL=false
TEST=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--ssd) SSD=true ;;
        -h|--hdd) HDD=true ;;
        -c|--concurrency) CONCURRENCY=true ;;
        -f|--full) FULL=true ;;
        -t|--test) TEST=true ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done

# Check if fio supports --lat option
LAT_SUPPORTED=false
if command -v fio >/dev/null 2>&1; then
    if fio --help 2>/dev/null | grep -q "lat="; then
        LAT_SUPPORTED=true
    fi
fi
if [ "$LAT_SUPPORTED" = false ]; then
    echo "Warning: fio does not support --lat option (latency tracking disabled)" >&2
fi

# Test mode settings
if [ "$TEST" = true ]; then
    RUNTIME=15
    FILESIZE=100M
fi

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

	echo "This is ${rw_part}, block size = ${BLOCKSIZE}" >> "${OFNAME}"

	# Build lat option
	local lat_opt=""
	if [ "$LATENCY" = "true" ] && [ "$LAT_SUPPORTED" = "true" ]; then
		lat_opt="--lat=1"
	fi

	fio --filename=${TMPFILE} --sync=1 --rw=$rw_part $extra --bs=${BLOCKSIZE} --numjobs=${JOBS} --iodepth=${IODEPTH} --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} --direct=1 $lat_opt >> "${OFNAME}" && rm ${TMPFILE}

}

summarize_results() {
    local summary_file="${BASEDIR}/summary.txt"
    echo "Generating summary..." >&2

    local data=()
    data+=("Test|IOPS Read|IOPS Write|BW Read|BW Write|Lat Avg Read (us)|Lat Avg Write (us)|CPU|Bar")

    for file in "${BASEDIR}"/bm_*.txt; do
        [ -f "$file" ] || continue

        # Collect actual tests present in the file
        local tests_present=()
        while IFS= read -r line; do
            if [[ "$line" =~ ^This\ is\ (.+),\ block\ size\ =\ (.+)$ ]]; then
                tests_present+=("${BASH_REMATCH[1]} ${BASH_REMATCH[2]}")
            fi
        done < "$file"
        # Remove duplicates
        tests_present=($(printf '%s\n' "${tests_present[@]}" | sort | uniq))

        for test in "${tests_present[@]}"; do
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
                # Extract IOPS
                local iops=$(grep -A 50 "This is $test_type" "$file" | grep "IOPS=" | head -1 | cut -d= -f2)
                if [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
                    read_iops=$iops
                    [ -z "$read_iops" ] && echo "Debug: No read IOPS found for $test in $file" >&2
                elif [[ "$test_type" == randwrite ]] || [[ "$test_type" == write ]]; then
                    write_iops=$iops
                    [ -z "$write_iops" ] && echo "Debug: No write IOPS found for $test in $file" >&2
                fi

                # Extract BW
                if [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
                    read_bw=$(grep -A 50 "This is $test_type" "$file" | grep "read:" | sed 's/.*BW=\([^)]*\).*/\1/' | head -1 | cut -d' ' -f1)
                    [ -z "$read_bw" ] && echo "Debug: No read BW found for $test in $file" >&2
                elif [[ "$test_type" == randwrite ]] || [[ "$test_type" == write ]]; then
                    write_bw=$(grep -A 50 "This is $test_type" "$file" | grep "write:" | sed 's/.*BW=\([^)]*\).*/\1/' | head -1 | cut -d' ' -f1)
                    [ -z "$write_bw" ] && echo "Debug: No write BW found for $test in $file" >&2
                fi

                # Extract Lat
                if [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
                    read_lat=$(grep -A 50 "This is $test_type" "$file" | grep "read:" -A 20 | grep "clat" | sed 's/.*avg=\([0-9.]*\).*/\1/' | head -1)
                    [ -z "$read_lat" ] && echo "Debug: No read lat found for $test in $file" >&2
                elif [[ "$test_type" == randwrite ]] || [[ "$test_type" == write ]]; then
                    write_lat=$(grep -A 50 "This is $test_type" "$file" | grep "write:" -A 20 | grep "clat" | sed 's/.*avg=\([0-9.]*\).*/\1/' | head -1)
                    [ -z "$write_lat" ] && echo "Debug: No write lat found for $test in $file" >&2
                fi

                # Extract CPU
                cpu=$(grep -A 50 "This is $test_type" "$file" | grep "cpu" -A 1 | grep "usr=" | head -1 | sed 's/.*usr=\([0-9.]*%\), sys=\([0-9.]*%\).*/usr=\1 sys=\2/')
                [ -z "$cpu" ] && echo "Debug: No CPU found for $test in $file" >&2
            fi

            [ -z "$read_iops" ] && read_iops="N/A"
            [ -z "$write_iops" ] && write_iops="N/A"
            [ -z "$read_bw" ] && read_bw="N/A"
            [ -z "$write_bw" ] && write_bw="N/A"
            [ -z "$read_lat" ] && read_lat="N/A"
            [ -z "$write_lat" ] && write_lat="N/A"
            [ -z "$cpu" ] && cpu="N/A"

            data+=("$test|$read_iops|$write_iops|$read_bw|$write_bw|$read_lat|$write_lat|$cpu|")
        done
    done

    # Output
    local table=$(printf '%s\n' "${data[@]}")
    if command -v column >/dev/null 2>&1; then
        table=$(echo "$table" | column -t -s '|')
    fi
    echo "$table"
    echo "$table" > "$summary_file"
    echo "Summary saved to $summary_file" >&2
}

if [ "$TEST" = false ]; then
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
else
    # Test mode: partial tests for quick validation
    do_disk_test "4k" "${OFNAME1}" "randread" false true $DEFAULT_JOBS $DEFAULT_IODEPTH
    do_disk_test "64k" "${OFNAME2}" "randwrite" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
    do_disk_test "1M" "${OFNAME3}" "read" true true $DEFAULT_JOBS $DEFAULT_IODEPTH
fi

# Generate summary
summarize_results

