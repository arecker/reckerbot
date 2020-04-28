#!/bin/sh -e

log() {
    echo "build.sh: $1"
}

ARCH="$(arch)"
VERSION="$(cat VERSION)"
IMAGE="arecker/reckerbot:${VERSION}-${ARCH}"

log "building $IMAGE"
docker build -t "$IMAGE" .

log "publishing $IMAGE"
docker push "$IMAGE"
