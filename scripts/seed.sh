#!/bin/sh

for secret in rtm web; do
    pass "reckerbot/${secret}-token" > "secrets/${secret}-token"
done
