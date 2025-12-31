#!/usr/bin/env bash
#set -x

# A few test on disk io performance using fio

# Environment variables

# Parameters to use
# FILESIZE=1G   # For testing only
FILESIZE=10G

# RUNTIME=15    # For testing only
RUNTIME=300

# Default file size for calculations (in MB)
FILESIZE_MB=10240
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
QUICK=false

# Individual test type flags
RANDREAD=false
RANDWRITE=false
READ=false
WRITE=false
RANDRW=false

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
        --quick) QUICK=true ;;
        --randread) RANDREAD=true ;;
        --randwrite) RANDWRITE=true ;;
        --read) READ=true ;;
        --write) WRITE=true ;;
        --randrw) RANDRW=true ;;
        --4k) BS_4K=true ;;
        --64k) BS_64K=true ;;
        --1M) BS_1M=true ;;
        --512k) BS_512K=true ;;
        --filesize) FILESIZE="$2"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done

# Validate flags
# Calculate file size in MB for runtime estimation
calculate_filesize_mb() {
    local size=$1
    local value=$(echo "$size" | sed 's/[A-Za-z]*$//')
    local unit=$(echo "$size" | sed 's/[0-9.]*//')

    case $unit in
        G|g) FILESIZE_MB=$((value * 1024)) ;;
        M|m) FILESIZE_MB=$value ;;
        K|k) FILESIZE_MB=$((value / 1024)) ;;
        *) FILESIZE_MB=$((value * 1024)) ;;  # Default to GB
    esac
}

calculate_filesize_mb "$FILESIZE"

# Quick mode: small file size and shorter runtime for testing
if [ "$QUICK" = true ]; then
    FILESIZE="1G"
    FILESIZE_MB=1024
    RUNTIME=15
    echo "Quick mode: Using 1G file size, 15s runtime per test" >&2
fi

validate_flags() {
    local individual_tests=false
    local block_sizes=false

    # Check if any individual test flags are set
    if [ "$RANDREAD" = true ] || [ "$RANDWRITE" = true ] || [ "$READ" = true ] || \
       [ "$WRITE" = true ] || [ "$RANDRW" = true ]; then
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
}

validate_flags

# Determine mode
INDIVIDUAL_TESTS=false
if [ "$RANDREAD" = true ] || [ "$RANDWRITE" = true ] || [ "$READ" = true ] || \
   [ "$WRITE" = true ] || [ "$RANDRW" = true ]; then
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

	# Record wall-clock start time
	local test_start_time=$(date +%s)

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

	# Record wall-clock end time and calculate duration
	local test_end_time=$(date +%s)
	local wall_clock_duration=$((test_end_time - test_start_time))

	# Append wall-clock duration to output file
	echo "" >> "${OFNAME}"
	echo "Wall-clock duration: ${wall_clock_duration}s" >> "${OFNAME}"

	rm -f ${TMPFILE}
}

summarize_results() {
    local summary_file="${RESULTS_DIR}/summary.txt"
    echo "Generating summary..." >&2

    local data=()
    data+=("Test|IOPS Read|IOPS Write|BW Read|BW Write|Lat Avg Read (us)|Lat Avg Write (us)|CPU|I/O Time|Wall Time|Status")

    # Get all benchmark files once to avoid duplicate processing
    local files=($(find "${RESULTS_DIR}" -maxdepth 1 -type f \( -name "bm_*.txt" -o -name "bm_*_individual.txt" \)))

    for file in "${files[@]}"; do
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
            if [[ "$test_type" != "randread" && "$test_type" != "randwrite" && "$test_type" != "read" && "$test_type" != "write" && "$test_type" != "randrw" ]]; then
                continue
            fi

            local read_iops="N/A"
            local write_iops="N/A"
            local read_bw="N/A"
            local write_bw="N/A"
            local read_lat="N/A"
            local write_lat="N/A"
            local cpu="N/A"
            local io_time="N/A"
            local wall_time="N/A"
            local status="OK"

            # Check if test was skipped
            if grep -q "SKIPPED:" "$file"; then
                status="SKIPPED"
                local skip_reason=$(grep "SKIPPED:" "$file" | sed 's/SKIPPED: //' | head -1)
                # For skipped tests, show reason in status column
                status="$skip_reason"
                io_time="N/A"
                wall_time="N/A"
                cpu="N/A"
            # Check if test failed (FIO error)
            elif grep -q "err=[0-9]" "$file" && ! grep -q "err= 0:" "$file"; then
                status="FAILED"
                local error_msg=$(grep "fio:.*err=" "$file" | sed 's/.*error=\(.*\)/\1/' | head -1)
                status="FAILED: $error_msg"
            fi

            # Extract I/O time (format: run=300098-300098msec)
            local test_io_time_ms=$(grep -A 50 "This is $test_type" "$file" | grep "run=" | head -1 | sed 's/.*run=\([0-9]*\)-[0-9]*msec.*/\1/')
            if [ -n "$test_io_time_ms" ] && [ "$test_io_time_ms" -gt 0 ]; then
                if [ "$test_io_time_ms" -lt 1000 ]; then
                    # Sub-second I/O time, display in milliseconds
                    io_time="${test_io_time_ms}ms"
                else
                    local io_time_sec=$((test_io_time_ms / 1000))
                    local hours=$((io_time_sec / 3600))
                    local minutes=$(((io_time_sec % 3600) / 60))
                    local seconds=$((io_time_sec % 60))
                    if [ $hours -gt 0 ]; then
                        io_time=$(printf "%02d:%02d:%02d" $hours $minutes $seconds)
                    else
                        io_time=$(printf "%02d:%02d" $minutes $seconds)
                    fi
                fi
            fi

            # Extract wall-clock duration
            local test_wall_time=$(grep -A 60 "This is $test_type" "$file" | grep "Wall-clock duration:" | head -1 | sed 's/.*Wall-clock duration: \([0-9]*\)s.*/\1/')
            if [ -n "$test_wall_time" ] && [ "$test_wall_time" -gt 0 ]; then
                local hours=$((test_wall_time / 3600))
                local minutes=$(((test_wall_time % 3600) / 60))
                local seconds=$((test_wall_time % 60))
                if [ $hours -gt 0 ]; then
                    wall_time=$(printf "%02d:%02d:%02d" $hours $minutes $seconds)
                elif [ $minutes -gt 0 ]; then
                    wall_time=$(printf "%02d:%02d" $minutes $seconds)
                else
                    wall_time="${seconds}s"
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

            [ -z "$read_iops" ] && read_iops="N/A"
            [ -z "$write_iops" ] && write_iops="N/A"
            [ -z "$read_bw" ] && read_bw="N/A"
            [ -z "$write_bw" ] && write_bw="N/A"
            [ -z "$read_lat" ] && read_lat="N/A"
            [ -z "$write_lat" ] && write_lat="N/A"
            [ -z "$cpu" ] && cpu="N/A"
            [ -z "$io_time" ] && io_time="N/A"
            [ -z "$wall_time" ] && wall_time="N/A"
            [ -z "$status" ] && status="N/A"

            data+=("$test|$read_iops|$write_iops|$read_bw|$write_bw|$read_lat|$write_lat|$cpu|$io_time|$wall_time|$status")
        done
    done

    # Output
    local table=$(printf '%s\n' "${data[@]}")
    if command -v column >/dev/null 2>&1; then
        table=$(echo "$table" | column -t -s '|')
    fi
    echo "$table"
    echo "$table" > "$summary_file"

    # Calculate total I/O time from all test files (in milliseconds)
    local total_io_time_ms=0
    local total_wall_time_sec=0
    local files=($(find "${RESULTS_DIR}" -maxdepth 1 -type f \( -name "bm_*.txt" -o -name "bm_*_individual.txt" \)))
    for file in "${files[@]}"; do
        [ -f "$file" ] || continue
        # Sum all run= values in the file (each test section has one)
        while read -r io_time_val; do
            if [ -n "$io_time_val" ] && [ "$io_time_val" -gt 0 ] 2>/dev/null; then
                total_io_time_ms=$((total_io_time_ms + io_time_val))
            fi
        done < <(grep "run=" "$file" | sed 's/.*run=\([0-9]*\)-[0-9]*msec.*/\1/')
        # Sum all wall-clock durations
        while read -r wall_time_val; do
            if [ -n "$wall_time_val" ] && [ "$wall_time_val" -gt 0 ] 2>/dev/null; then
                total_wall_time_sec=$((total_wall_time_sec + wall_time_val))
            fi
        done < <(grep "Wall-clock duration:" "$file" | sed 's/.*Wall-clock duration: \([0-9]*\)s.*/\1/')
    done

    # Format total I/O time
    local total_io_display
    if [ "$total_io_time_ms" -lt 1000 ]; then
        total_io_display="${total_io_time_ms}ms"
    else
        local total_io_seconds=$((total_io_time_ms / 1000))
        local io_hours=$((total_io_seconds / 3600))
        local io_minutes=$(((total_io_seconds % 3600) / 60))
        local io_seconds=$((total_io_seconds % 60))
        if [ $io_hours -gt 0 ]; then
            total_io_display=$(printf "%02d:%02d:%02d" $io_hours $io_minutes $io_seconds)
        else
            total_io_display=$(printf "%02d:%02d" $io_minutes $io_seconds)
        fi
    fi

    # Format total wall time
    local total_wall_display
    local wall_hours=$((total_wall_time_sec / 3600))
    local wall_minutes=$(((total_wall_time_sec % 3600) / 60))
    local wall_seconds=$((total_wall_time_sec % 60))
    if [ $wall_hours -gt 0 ]; then
        total_wall_display=$(printf "%02d:%02d:%02d" $wall_hours $wall_minutes $wall_seconds)
    elif [ $wall_minutes -gt 0 ]; then
        total_wall_display=$(printf "%02d:%02d" $wall_minutes $wall_seconds)
    else
        total_wall_display="${wall_seconds}s"
    fi

    # Add timestamp, total runtimes, and note to summary
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "" | tee -a "$summary_file"
    echo "Test completed: $timestamp" | tee -a "$summary_file"
    echo "Total I/O time: $total_io_display (actual disk I/O operations)" | tee -a "$summary_file"
    echo "Total wall time: $total_wall_display (including setup/teardown)" | tee -a "$summary_file"
    echo "" | tee -a "$summary_file"
    echo "Note: I/O Time = FIO disk operation duration. Wall Time = total elapsed time including file creation and cleanup." | tee -a "$summary_file"

    echo "Summary saved to $summary_file" >&2
}

run_individual_tests() {
    local test_types=("randread" "randwrite" "read" "write" "randrw")
    local block_sizes=("4k" "64k" "1M" "512k")
    local type_vars=("RANDREAD" "RANDWRITE" "READ" "WRITE" "RANDRW")
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
fi

# Generate summary
summarize_results
