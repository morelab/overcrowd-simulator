#!/bin/bash
rm devices.csv
threads=${1-8}
echo Using $threads threads

for c in conf_0 conf_1 conf_2 conf_3 conf_4;
do
        echo Running with $c
        spark-submit --master local[$threads] experiment/runner.py --threads $threads --output cells_$threads.csv --conf experiment.devices.$c
done
