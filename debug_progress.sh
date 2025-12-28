#!/usr/bin/env bash
# Debug test for \r behavior in terminal
echo "Test 1: Simple \\r without formatting" >&2
echo -ne "Line 1\r" >&2
sleep 1
echo -ne "Line 2\r" >&2
sleep 1
echo -ne "Line 3\r" >&2
sleep 1
echo "Done" >&2
echo "" >&2

echo "Test 2: \\r with printf" >&2
printf "Line 1\r" >&2
sleep 1
printf "Line 2\r" >&2
sleep 1
printf "Line 3\r" >&2
sleep 1
echo "Done" >&2
echo "" >&2

echo "Test 3: Using tput cr" >&2
tput cr; printf "Line 1" >&2
sleep 1
tput cr; printf "Line 2" >&2
sleep 1
tput cr; printf "Line 3" >&2
sleep 1
echo "Done" >&2
echo "" >&2

echo "Test 4: Using tput cr + el (clear line)" >&2
tput cr; tput el; printf "Line 1" >&2
sleep 1
tput cr; tput el; printf "Line 2" >&2
sleep 1
tput cr; tput el; printf "Line 3" >&2
sleep 1
echo "Done" >&2
echo "" >&2

echo "Test 5: Progress bar simulation" >&2
for i in {1..3}; do
    progress=$((i * 10))
    bar=$(printf '%*s' "$progress" '' | tr ' ' '#')
    printf "Progress: [%-20s] %3d%%\r" "$bar" "$progress"
    sleep 1
done
echo "" >&2
echo "All tests completed" >&2
