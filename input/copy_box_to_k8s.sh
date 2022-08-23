#!/bin/bash

pod=$(kubectl -n esida get pod | grep esida-db | awk '{ print $1 }')

kubectl cp data/MARS/ESIDADarEsSalaam_LINUX.zip esida/"$pod":/app/input/data/MARS/ESIDADarEsSalaam_LINUX.zip
kubectl cp data/MARS/ESIDADarEsSalaam_MACOSX.zip esida/"$pod":/app/input/data/MARS/ESIDADarEsSalaam_MACOSX.zip
kubectl cp data/MARS/ESIDADarEsSalaam_WINDOWS.zip esida/"$pod":/app/input/data/MARS/ESIDADarEsSalaam_WINDOWS.zip
kubectl cp data/MARS/ESIDADarEsSalaam_MACARM64.zip esida/"$pod":/app/input/data/MARS/ESIDADarEsSalaam_MACARM64.zip
