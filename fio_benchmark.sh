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

# Create results directory for all output files
RESULTS_DIR="${BASEDIR}/results"
mkdir -p "${RESULTS_DIR}"

# Clean previous output files
rm -f "${RESULTS_DIR}"/bm_*.txt "${RESULTS_DIR}"/summary.txt
 
OFNAME1="${RESULTS_DIR}/bm_4k.txt"
OFNAME2="${RESULTS_DIR}/bm_64k.txt"
OFNAME3="${RESULTS_DIR}/bm_1M.txt"
OFNAME4="${RESULTS_DIR}/bm_512k.txt"

# Flag parsing (support both short and long options)
SSD=false
HDD=false
CONCURRENCY=false
FULL=false
TEST=false

# Individual test type flags
RANDREAD=false
RANDWRITE=false
READ=false
WRITE=false
RANDRW=false
TRIM=false

# Block size flags
BS_4K=false
BS_64K=false
BS_1M=false
BS_512K=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--ssd) SSD=true ;;
        -h|--hdd) HDD=true ;;
        -c|--concurrency) CONCURRENCY=true ;;
        -f|--full) FULL=true ;;
        -t|--test) TEST=true ;;
        --randread) RANDREAD=true ;;
        --randwrite) RANDWRITE=true ;;
        --read) READ=true ;;
        --write) WRITE=true ;;
        --randrw) RANDRW=true ;;
        --trim) TRIM=true ;;
        --4k) BS_4K=true ;;
        --64k) BS_64K=true ;;
        --1M) BS_1M=true ;;
        --512k) BS_512K=true ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done

# Validate flags
validate_flags() {
    local individual_tests=false
    local block_sizes=false

    # Check if any individual test flags are set
    if [ "$RANDREAD" = true ] || [ "$RANDWRITE" = true ] || [ "$READ" = true ] || \
       [ "$WRITE" = true ] || [ "$RANDRW" = true ] || [ "$TRIM" = true ]; then
        individual_tests=true
    fi

    # Check if any block size flags are set
    if [ "$BS_4K" = true ] || [ "$BS_64K" = true ] || [ "$BS_1M" = true ] || [ "$BS_512K" = true ]; then
        block_sizes=true
    fi

    # Check for mode conflicts
    if [ "$individual_tests" = true ]; then
        if [ "$TEST" = true ] || [ "$FULL" = true ]; then
            echo "Error: Individual test flags cannot be combined with --test or --full" >&2
            echo "Please use either --test/--full OR individual test flags, not both." >&2
            exit 1
        fi

        if [ "$block_sizes" = false ]; then
            echo "Error: Individual test flags require at least one block size (--4k, --64k, --1M, --512k)" >&2
            exit 1
        fi
    fi

    # Validate trim requires SSD
    if [ "$TRIM" = true ] && [ "$SSD" = false ]; then
        echo "Error: --trim flag requires --ssd flag" >&2
        exit 1
    fi
}

validate_flags

# Determine mode
INDIVIDUAL_TESTS=false
if [ "$RANDREAD" = true ] || [ "$RANDWRITE" = true ] || [ "$READ" = true ] || \
   [ "$WRITE" = true ] || [ "$RANDRW" = true ] || [ "$TRIM" = true ]; then
    INDIVIDUAL_TESTS=true
fi

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
 elif [ "$INDIVIDUAL_TESTS" = true ]; then
    # Calculate total tests based on selected types and block sizes
    test_types=0
    [ "$RANDREAD" = true ] && test_types=$((test_types + 1))
    [ "$RANDWRITE" = true ] && test_types=$((test_types + 1))
    [ "$READ" = true ] && test_types=$((test_types + 1))
    [ "$WRITE" = true ] && test_types=$((test_types + 1))
    [ "$RANDRW" = true ] && test_types=$((test_types + 1))
    [ "$TRIM" = true ] && test_types=$((test_types + 1))

    block_count=0
    [ "$BS_4K" = true ] && block_count=$((block_count + 1))
    [ "$BS_64K" = true ] && block_count=$((block_count + 1))
    [ "$BS_1M" = true ] && block_count=$((block_count + 1))
    [ "$BS_512K" = true ] && block_count=$((block_count + 1))

    total_tests=$((test_types * block_count))
    total_runtime=$((total_tests * RUNTIME))
else
    total_tests=14
    total_runtime=4200
fi

format_time() {
    local s=$1
    printf '%02d:%02d:%02d' $((s / 3600)) $((s % 3600 / 60)) $((s % 60))
}

# Set concurrency defaults
CONC_JOBS=1
CONC_IODEPTH=4
if [ "$CONCURRENCY" = true ]; then
    CONC_JOBS=4
    CONC_IODEPTH=16
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

	if [ -n "$extra" ]; then
		fio --filename=${TMPFILE} --sync=1 --rw=$rw_part --${extra} --bs=${BLOCKSIZE} --numjobs=${JOBS} --iodepth=${IODEPTH} --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} --direct=1 >> "${OFNAME}" &
	else
		fio --filename=${TMPFILE} --sync=1 --rw=$rw_part --bs=${BLOCKSIZE} --numjobs=${JOBS} --iodepth=${IODEPTH} --group_reporting --name=${TESTNAME} --filesize=${FILESIZE} --runtime=${RUNTIME} --direct=1 >> "${OFNAME}" &
	fi
	pid=$!
	while kill -0 $pid 2>/dev/null; do
	    elapsed=$(($(date +%s) - start_time))
	    remaining=$((total_runtime - elapsed))
	    if [ "$remaining" -lt 0 ]; then remaining=0; fi
	    if [ "$INDIVIDUAL_TESTS" = false ]; then
	        progress=$((current_test * 20 / total_tests))
	        bar=$(printf '%*s' "$progress" '' | tr ' ' '#'; printf '%*s' "$((20 - progress))" '' | tr ' ' ' ')
 	    msg="Progress: [$bar] $((current_test * 100 / total_tests))% | Running: $current_test_name | Elapsed: $(format_time $elapsed) | Remaining: ~$(format_time $remaining) (approximate)"
 	    else
 	        msg="Running: $current_test_name | Elapsed: $(format_time $elapsed) | Remaining: ~$(format_time $remaining) (approximate)"
	    fi
	    printf "%s\r" "$msg" >&2
	    sleep 10
	done
	wait $pid
	# Clear progress line from terminal
	printf "\r%-${width}s" "                                                                                                                                    " >&2
	echo "" >&2
	rm -f ${TMPFILE}
}

summarize_results() {
    local summary_file="${RESULTS_DIR}/summary.txt"
    echo "Generating summary..." >&2
 
    local data=()
    data+=("Test|IOPS Read|IOPS Write|BW Read|BW Write|Lat Avg Read (us)|Lat Avg Write (us)|CPU|Runtime")
 
    for file in "${RESULTS_DIR}"/bm_*.txt "${RESULTS_DIR}"/bm_*_individual.txt; do
        [ -f "$file" ] || continue

        # Collect actual tests present in file
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
            if [[ "$test_type" != "randread" && "$test_type" != "randwrite" && "$test_type" != "read" && "$test_type" != "write" && "$test_type" != "randrw" && "$test_type" != "trim" ]]; then
                continue
            fi

            local read_iops="N/A"
            local write_iops="N/A"
            local read_bw="N/A"
            local write_bw="N/A"
            local read_lat="N/A"
            local write_lat="N/A"
            local cpu="N/A"
            local runtime="N/A"

            if [ "$test_type" != "trim" ]; then
                # Extract runtime (format: run=300098-300098msec)
                local test_runtime_ms=$(grep -A 50 "This is $test_type" "$file" | grep "run=" | head -1 | sed 's/.*run=\([0-9]*\)-[0-9]*msec.*/\1/')
                if [ -n "$test_runtime_ms" ]; then
                    local runtime_sec=$((test_runtime_ms / 1000))
                    local hours=$((runtime_sec / 3600))
                    local minutes=$(((runtime_sec % 3600) / 60))
                    local seconds=$((runtime_sec % 60))
                    if [ $hours -gt 0 ]; then
                        runtime=$(printf "%02d:%02d:%02d" $hours $minutes $seconds)
                    else
                        runtime=$(printf "%02d:%02d" $minutes $seconds)
                    fi
                fi

                # Extract IOPS
                local iops=$(grep -A 50 "This is $test_type" "$file" | grep "IOPS=" | head -1 | sed 's/.*IOPS=\([0-9.k]*\).*/\1/')
                if [[ "$test_type" == randrw ]]; then
                    # Special handling for randrw - extract both read and write metrics
                    read_iops=$(grep "read:" "$file" | grep "IOPS=" | head -1 | sed 's/.*IOPS=\([0-9.]*\).*/\1/')
                    write_iops=$(grep "write:" "$file" | grep "IOPS=" | head -1 | sed 's/.*IOPS=\([0-9.]*\).*/\1/')
                elif [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
                    read_iops=$iops
                elif [[ "$test_type" == randwrite ]] || [[ "$test_type" == write ]]; then
                    write_iops=$iops
                fi

                # Extract BW
                if [[ "$test_type" == randrw ]]; then
                    read_bw=$(grep "read:" "$file" | grep "BW=" | head -1 | sed 's/.*BW=\([^)]*\).*/\1/' | cut -d' ' -f1)
                    write_bw=$(grep "write:" "$file" | grep "BW=" | head -1 | sed 's/.*BW=\([^)]*\).*/\1/' | cut -d' ' -f1)
                elif [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
                    read_bw=$(grep -A 50 "This is $test_type" "$file" | grep "read:" | sed 's/.*BW=\([^)]*\).*/\1/' | head -1 | cut -d' ' -f1)
                elif [[ "$test_type" == randwrite ]] || [[ "$test_type" == write ]]; then
                    write_bw=$(grep -A 50 "This is $test_type" "$file" | grep "write:" | sed 's/.*BW=\([^)]*\).*/\1/' | head -1 | cut -d' ' -f1)
                fi

                # Extract Lat
                if [[ "$test_type" == randrw ]]; then
                    read_lat=$(grep "read:" "$file" -A 20 | grep "clat" | head -1 | sed 's/.*avg=\([0-9.]*\).*/\1/')
                    write_lat=$(grep "write:" "$file" -A 20 | grep "clat" | head -1 | sed 's/.*avg=\([0-9.]*\).*/\1/')
                elif [[ "$test_type" == randread ]] || [[ "$test_type" == read ]]; then
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
            [ -z "$runtime" ] && runtime="N/A"

            data+=("$test|$read_iops|$write_iops|$read_bw|$write_bw|$read_lat|$write_lat|$cpu|$runtime")
        done
    done

    # Output
    local table=$(printf '%s\n' "${data[@]}")
    if command -v column >/dev/null 2>&1; then
        table=$(echo "$table" | column -t -s '|')
    fi
    echo "$table"
    echo "$table" > "$summary_file"

    # Calculate total runtime from all test files
    local total_runtime_seconds=0
    for file in "${BASEDIR}"/bm_*.txt "${BASEDIR}"/bm_*_individual.txt; do
        [ -f "$file" ] || continue
        local test_runtime_ms=$(grep "run=" "$file" | head -1 | sed 's/.*run=\([0-9]*\)-[0-9]*msec.*/\1/')
        if [ -n "$test_runtime_ms" ]; then
            total_runtime_seconds=$((total_runtime_seconds + test_runtime_ms / 1000))
        fi
    done

    # Format total runtime
    local total_hours=$((total_runtime_seconds / 3600))
    local total_minutes=$(((total_runtime_seconds % 3600) / 60))
    local total_seconds=$((total_runtime_seconds % 60))
    local total_display
    if [ $total_hours -gt 0 ]; then
        total_display=$(printf "%02d:%02d:%02d" $total_hours $total_minutes $total_seconds)
    else
        total_display=$(printf "%02d:%02d" $total_minutes $total_seconds)
    fi

    # Add timestamp, total runtime, and note to summary
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "" | tee -a "$summary_file"
    echo "Test completed: $timestamp" | tee -a "$summary_file"
    echo "Total runtime: $total_display" | tee -a "$summary_file"
    echo "" | tee -a "$summary_file"
    echo "Note: Runtime values are approximate estimates. Actual times may vary based on disk performance and system load." | tee -a "$summary_file"

    echo "Summary saved to $summary_file" >&2
}

run_individual_tests() {
    local test_types=("randread" "randwrite" "read" "write" "randrw" "trim")
    local block_sizes=("4k" "64k" "1M" "512k")
    local type_vars=("RANDREAD" "RANDWRITE" "READ" "WRITE" "RANDRW" "TRIM")
    local size_vars=("BS_4K" "BS_64K" "BS_1M" "BS_512K")

    local i j
    for ((i=0; i<${#test_types[@]}; i++)); do
        local test_type="${test_types[$i]}"
        local type_var="${type_vars[$i]}"

        if [ "${!type_var}" = true ]; then
            for ((j=0; j<${#block_sizes[@]}; j++)); do
                local block_size="${block_sizes[$j]}"
                local size_var="${size_vars[$j]}"

                if [ "${!size_var}" = true ]; then
                    # Skip invalid combinations (trim only supports 4k)
                    if [ "$test_type" = "trim" ] && [ "$block_size" != "4k" ]; then
                        continue
                    fi

                    # Generate unique output filename
                    local output_file="${RESULTS_DIR}/bm_${test_type}_${block_size}_individual.txt"

                    # Set test name and description
                    if [ "$test_type" = "randrw" ]; then
                        current_test_name="Randrw ${block_size}"
                    elif [ "$test_type" = "randread" ]; then
                        current_test_name="Randread ${block_size}"
                    elif [ "$test_type" = "randwrite" ]; then
                        current_test_name="Randwrite ${block_size}"
                    elif [ "$test_type" = "read" ]; then
                        current_test_name="Read ${block_size}"
                    elif [ "$test_type" = "write" ]; then
                        current_test_name="Write ${block_size}"
                    elif [ "$test_type" = "trim" ]; then
                        current_test_name="Trim ${block_size}"
                    fi

                    # Determine testtype parameter
                    local testtype_param
                    if [ "$test_type" = "randrw" ]; then
                        testtype_param="randrw:rwmixread=70"
                    else
                        testtype_param="$test_type"
                    fi

                    # Run test
                    do_disk_test "$block_size" "$output_file" "$testtype_param" false $CONC_JOBS $CONC_IODEPTH
                fi
            done
        fi
    done
}

# Main test execution
if [ "$INDIVIDUAL_TESTS" = true ]; then
    run_individual_tests
elif [ "$TEST" = true ]; then
    # Test mode: partial tests for quick validation
    current_test_name="Random Read 4k"
    do_disk_test "4k" "${OFNAME1}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 64k"
    do_disk_test "64k" "${OFNAME2}" "randwrite" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Read 1M"
    do_disk_test "1M" "${OFNAME3}" "read" true $CONC_JOBS $CONC_IODEPTH
elif [ "$FULL" = true ]; then
    # Full mode: run all lean tests + 512k block sizes
    # Do test for block sizes 4 KiB, 64 KiB, and 1 MiB, respectively.
    current_test_name="Random Read 4k"
    do_disk_test "4k" "${OFNAME1}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 4k"
    do_disk_test "4k" "${OFNAME1}" "randwrite" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Read 4k"
    do_disk_test "4k" "${OFNAME1}" "read" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Write 4k"
    do_disk_test "4k" "${OFNAME1}" "write" true $CONC_JOBS $CONC_IODEPTH

    current_test_name="Random Read 64k"
    do_disk_test "64k" "${OFNAME2}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 64k"
    do_disk_test "64k" "${OFNAME2}" "randwrite" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Read 64k"
    do_disk_test "64k" "${OFNAME2}" "read" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Write 64k"
    do_disk_test "64k" "${OFNAME2}" "write" true $CONC_JOBS $CONC_IODEPTH

    current_test_name="Random Read 1M"
    do_disk_test "1M" "${OFNAME3}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 1M"
    do_disk_test "1M" "${OFNAME3}" "randwrite" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Read 1M"
    do_disk_test "1M" "${OFNAME3}" "read" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Write 1M"
    do_disk_test "1M" "${OFNAME3}" "write" true $CONC_JOBS $CONC_IODEPTH

    # Lean additional tests
    LEAN_RUNTIME=60

    # Mixed RandRW
    RUNTIME=$LEAN_RUNTIME
    current_test_name="Randrw 4k"
    do_disk_test "4k" "${RESULTS_DIR}/bm_randrw.txt" "randrw:rwmixread=70" false $CONC_JOBS $CONC_IODEPTH

    # Trim for SSD
    if [ "$SSD" = true ]; then
        current_test_name="Trim 4k"
        do_disk_test "4k" "${RESULTS_DIR}/bm_trim.txt" "trim" false $CONC_JOBS $CONC_IODEPTH
    fi

    # Full mode: additional 512k tests
    RUNTIME=300
    current_test_name="Random Read 512k"
    do_disk_test "512k" "${OFNAME4}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 512k"
    do_disk_test "512k" "${OFNAME4}" "randwrite" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Read 512k"
    do_disk_test "512k" "${OFNAME4}" "read" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Write 512k"
    do_disk_test "512k" "${OFNAME4}" "write" true $CONC_JOBS $CONC_IODEPTH
else
    # Lean mode (default): run all original tests with enhancements
    # Do test for block sizes 4 KiB, 64 KiB, and 1 MiB, respectively.
    current_test_name="Random Read 4k"
    do_disk_test "4k" "${OFNAME1}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 4k"
    do_disk_test "4k" "${OFNAME1}" "randwrite" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Read 4k"
    do_disk_test "4k" "${OFNAME1}" "read" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Write 4k"
    do_disk_test "4k" "${OFNAME1}" "write" true $CONC_JOBS $CONC_IODEPTH

    current_test_name="Random Read 64k"
    do_disk_test "64k" "${OFNAME2}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 64k"
    do_disk_test "64k" "${OFNAME2}" "randwrite" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Read 64k"
    do_disk_test "64k" "${OFNAME2}" "read" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Write 64k"
    do_disk_test "64k" "${OFNAME2}" "write" true $CONC_JOBS $CONC_IODEPTH

    current_test_name="Random Read 1M"
    do_disk_test "1M" "${OFNAME3}" "randread" false $CONC_JOBS $CONC_IODEPTH
    current_test_name="Random Write 1M"
    do_disk_test "1M" "${OFNAME3}" "randwrite" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Read 1M"
    do_disk_test "1M" "${OFNAME3}" "read" true $CONC_JOBS $CONC_IODEPTH
    current_test_name="Sequential Write 1M"
    do_disk_test "1M" "${OFNAME3}" "write" true $CONC_JOBS $CONC_IODEPTH

    # Lean additional tests
    LEAN_RUNTIME=60

    # Mixed RandRW
    RUNTIME=$LEAN_RUNTIME
    current_test_name="Randrw 4k"
    do_disk_test "4k" "${RESULTS_DIR}/bm_randrw.txt" "randrw:rwmixread=70" false $CONC_JOBS $CONC_IODEPTH

    # Trim for SSD
    if [ "$SSD" = true ]; then
        current_test_name="Trim 4k"
        do_disk_test "4k" "${RESULTS_DIR}/bm_trim.txt" "trim" false $CONC_JOBS $CONC_IODEPTH
    fi
fi

# Generate summary
summarize_results
