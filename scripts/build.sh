#!/usr/bin/env bash

set -e

VERSION="$(git describe)"
PLATFORMS="linux/386,linux/amd64,linux/arm/v6,linux/arm/v7,linux/arm64"
IMAGE_NAME="arecker/reckerbot"

log() {
    echo "build.sh: $1" 1>&2;
}

head_is_a_tag() {
    git describe --exact-match > /dev/null
    [ "$?" == "0" ]
}

docker_build() {
    docker buildx build \
	   --platform "$1" \
	   --output "type=image,push=true" \
	   --tag "${IMAGE_NAME}:${VERSION}" \
	   --tag "${IMAGE_NAME}:latest" \
	   --file Dockerfile .
}

if head_is_a_tag; then
    log "starting build for version $VERSION"
else
    log "$VERSION is not an exact tag.  Exiting..."
    exit 0
fi

log "building $IMAGE_NAME"
docker_build "$PLATFORMS"
