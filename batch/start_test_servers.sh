#!/bin/bash
python -m labrad.node &
python ../okfpga/test_okfpga.py &
python ../sequencer/test_sequencer.py &

cd ../conductor
python conductor.py

PGID=$(ps pgid= $PID | grep -o [0-9]*)
function cleanup() {
    echo "Killing Labrad servers"
    kill -INT -"$PGID"
}
trap cleanup SIGINT