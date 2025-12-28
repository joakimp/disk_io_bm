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

# Test mode settings
if [ "$TEST" = true ]; then
    RUNTIME=15
    FILESIZE=100M
fi

# Progress tracking
start_time=$(date +%s)
current_test=0
if [ "$TEST" = true ]; then
    total_tests=3
    total_runtime=45
elif [ "$FULL" = true ]; then
    total_tests=18
    total_runtime=7200
else
    total_tests=14
    total_runtime=4200
fi

format_time() {
    local s=$1
    printf '%02d:%02d:%02d' $((s / 3600)) $((s % 3600 / 60)) $((s % 60))
}





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
	# Expected parameters: block size, outfile, type of test, append mode, numjobs, iodepth
	# All other used variables are globally known.
	local BLOCKSIZE="$1"
	local OFNAME="$2"
	local TESTTYPE="$3"
	local APPEND="$4"
	local JOBS="$5"
	local IODEPTH="$6"

	current_test=$((current_test + 1))

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

	fio --filename=${TMPFILE} --sync=1 --rw=$rw_part $extra --bs=${BLOCKSIZE} --numjobs=${JOBS} --iodepth=${IODEPTH} --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} --direct=1 >> "${OFNAME}" &
pid=$!
while kill -0 $pid 2>/dev/null; do
    elapsed=$(($(date +%s) - start_time))
    remaining=$((total_runtime - elapsed))
    if [ "$remaining" -lt 0 ]; then remaining=0; fi
    progress=$((current_test * 20 / total_tests))
    bar=$(printf '%*s' "$progress" '' | tr ' ' '#'; printf '%*s' "$((20 - progress))" '' | tr ' ' ' ')
    msg="Progress: [$bar] $((current_test * 100 / total_tests))% | Running: $current_test_name | Elapsed: $(format_time $elapsed) | Remaining: ~$(format_time $remaining)"
    printf "%s\r" "$msg" >&2
    sleep 10
done
wait $pid
# Clear progress line from terminal
printf "\r%-${width}s" "                                                                                                                                    " >&2
echo "" >&2
rm ${TMPFILE}

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
        local seen=()
        local unique_tests=()
        for t in "${tests_present[@]}"; do
            if [[ ! " ${seen[*]} " =~ " $t " ]]; then
                seen+=("$t")
                unique_tests+=("$t")
            fi
        done
        tests_present=("${unique_tests[@]}")

        for test in "${tests_present[@]}"; do
            local test_type=${test% *}
            local block=${test#* }
            # Skip invalid test types
            if [[ "$test_type" != "randread" && "$test_type" != "randwrite" && "$test_type" != "read" && "$test_type" != "write" && "$test_type" != "trim" ]]; then
                continue
            fi

            local read_iops="N/A"
            local write_iops="N/A"
            local read_bw="N/A"
            local write_bw="N/A"
            local read_lat="N/A"
            local write_lat="N/A"
            local cpu="N/A"

            if [ "$test_type" != "trim" ]; then
                # Extract IOPS
                local iops=$(grep -A 50 "This is $test_type" "$file" | grep "IOPS=" | head -1 | sed 's/.*IOPS=\([0-9.k]*\).*/\1/')
                if [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
                    read_iops=$iops
                elif [[ "$test_type" == randwrite ]] || [[ "$test_type" == write ]]; then
                    write_iops=$iops
                fi

                # Extract BW
                if [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
                    read_bw=$(grep -A 50 "This is $test_type" "$file" | grep "read:" | sed 's/.*BW=\([^)]*\).*/\1/' | head -1 | cut -d' ' -f1)
                elif [[ "$test_type" == randwrite ]] || [[ "$test_type" == write ]]; then
                    write_bw=$(grep -A 50 "This is $test_type" "$file" | grep "write:" | sed 's/.*BW=\([^)]*\).*/\1/' | head -1 | cut -d' ' -f1)
                fi

                # Extract Lat
                if [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
                    read_lat=$(grep -A 50 "This is $test_type" "$file" | grep "read:" -A 20 | grep "clat" | sed 's/.*avg=\([0-9.]*\).*/\1/' | head -1)
                elif [[ "$test_type" == randwrite ]] || [[ "$test_type" == write ]]; then
                    write_lat=$(grep -A 50 "This is $test_type" "$file" | grep "write:" -A 20 | grep "clat" | sed 's/.*avg=\([0-9.]*\).*/\1/' | head -1)
                fi

                # Extract CPU
                cpu=$(grep -A 50 "This is $test_type" "$file" | grep "cpu" -A 1 | grep "usr=" | head -1 | sed 's/.*usr=\([0-9.]*%\), sys=\([0-9.]*%\).*/usr=\1 sys=\2/')
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
    current_test_name="Random Read 4k"
    do_disk_test "4k" "${OFNAME1}" "randread" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Random Write 4k"
    do_disk_test "4k" "${OFNAME1}" "randwrite" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Sequential Read 4k"
    do_disk_test "4k" "${OFNAME1}" "read" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Sequential Write 4k"
    do_disk_test "4k" "${OFNAME1}" "write" false $DEFAULT_JOBS $DEFAULT_IODEPTH

    current_test_name="Random Read 64k"
    do_disk_test "64k" "${OFNAME2}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 64k"
    do_disk_test "64k" "${OFNAME2}" "randwrite" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Sequential Read 64k"
    do_disk_test "64k" "${OFNAME2}" "read" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Sequential Write 64k"
    do_disk_test "64k" "${OFNAME2}" "write" false $DEFAULT_JOBS $DEFAULT_IODEPTH

    current_test_name="Random Read 1M"
    do_disk_test "1M" "${OFNAME3}" "randread" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Random Write 1M"
    do_disk_test "1M" "${OFNAME3}" "randwrite" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Sequential Read 1M"
    do_disk_test "1M" "${OFNAME3}" "read" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Sequential Write 1M"
    do_disk_test "1M" "${OFNAME3}" "write" false $DEFAULT_JOBS $DEFAULT_IODEPTH

    # Lean additional tests
    LEAN_RUNTIME=60
    if [ "$FULL" = true ]; then LEAN_RUNTIME=300; fi

    # Mixed RandRW
    RUNTIME=$LEAN_RUNTIME
    current_test_name="Mixed Random Read/Write 4k"
    do_disk_test "4k" "${BASEDIR}/bm_mixed.txt" "randrw:rwmixread=70" false $DEFAULT_JOBS $DEFAULT_IODEPTH

    # Trim for SSD
    if [ "$SSD" = true ]; then
        current_test_name="Trim 4k"
        do_disk_test "4k" "${BASEDIR}/bm_trim.txt" "trim" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    fi

    # Full mode: additional 512k tests
    if [ "$FULL" = true ]; then
        RUNTIME=300
        current_test_name="Random Read 512k"
        do_disk_test "512k" "${OFNAME4}" "randread" false $DEFAULT_JOBS $DEFAULT_IODEPTH
        current_test_name="Random Write 512k"
        do_disk_test "512k" "${OFNAME4}" "randwrite" false $DEFAULT_JOBS $DEFAULT_IODEPTH
        current_test_name="Sequential Read 512k"
        do_disk_test "512k" "${OFNAME4}" "read" false $DEFAULT_JOBS $DEFAULT_IODEPTH
        current_test_name="Sequential Write 512k"
        do_disk_test "512k" "${OFNAME4}" "write" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    fi
else
    # Test mode: partial tests for quick validation
    current_test_name="Random Read 4k"
    do_disk_test "4k" "${OFNAME1}" "randread" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Random Write 64k"
    do_disk_test "64k" "${OFNAME2}" "randwrite" false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Sequential Read 1M"
    do_disk_test "1M" "${OFNAME3}" "read" false $DEFAULT_JOBS $DEFAULT_IODEPTH
fi

    # Full mode: additional 512k tests
    if [ "$FULL" = true ]; then
        RUNTIME=300
        current_test_name="Random Read 512k"
        do_disk_test "512k" "${OFNAME4}" "randread" false false $DEFAULT_JOBS $DEFAULT_IODEPTH
        current_test_name="Random Write 512k"
        do_disk_test "512k" "${OFNAME4}" "randwrite" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
        current_test_name="Sequential Read 512k"
        do_disk_test "512k" "${OFNAME4}" "read" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
        current_test_name="Sequential Write 512k"
        do_disk_test "512k" "${OFNAME4}" "write" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
    fi
else
    # Test mode: partial tests for quick validation
    current_test_name="Random Read 4k"
    do_disk_test "4k" "${OFNAME1}" "randread" false true $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Random Write 64k"
    do_disk_test "64k" "${OFNAME2}" "randwrite" true false $DEFAULT_JOBS $DEFAULT_IODEPTH
    current_test_name="Sequential Read 1M"
    do_disk_test "1M" "${OFNAME3}" "read" true true $DEFAULT_JOBS $DEFAULT_IODEPTH
fi

# Generate summary
summarize_results

