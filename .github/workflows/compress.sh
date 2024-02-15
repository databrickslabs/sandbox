#!/bin/bash

cd dist
    gzip *
    sha256sum * > SHA256SUMS
cd -