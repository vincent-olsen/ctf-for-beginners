#!/bin/bash

# makekey.sh
key="pitlrdhfczegoxyavujqkbmnswPITLRDHFCZEGOXYAVUJQKBMNSW"

cat mono.txt | tr 'a-zA-Z' $key > mono_enc.txt
