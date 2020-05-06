#!/bin/sh -e

VERSION="$(git describe)"
IMAGE_NAME="arecker/reckerbot"
PLATFORMS="linux/386,linux/amd64,linux/arm/v6,linux/arm/v7,linux/arm64"

docker buildx build \
       --platform "$PLATFORMS" \
       --output "type=image,push=true" \
       --tag "${IMAGE_NAME}:${VERSION}" \
       --tag "${IMAGE_NAME}:latest" \
       --file Dockerfile .
