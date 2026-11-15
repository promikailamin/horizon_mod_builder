# Portable Horizon native-build environment.
#
# Ubuntu 22.04 (Jammy) has glibc 2.35, the same baseline the official Horizon
# Linux binaries use. Building here keeps imported builds runnable on Ubuntu
# 22.04/24.04 and Debian 12, instead of requiring the GitHub runner's newer
# glibc (for example GLIBC_2.43 from Ubuntu 26.04).
FROM eclipse-temurin:25-jdk-jammy

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        libasound2-dev \
        libssl-dev \
        libudev-dev \
        libx11-xcb1 \
        libxcb-xkb1 \
        libxcb1 \
        libxkbcommon-x11-0 \
        libxkbcommon0 \
        pkg-config \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

LABEL org.opencontainers.image.title="horizon-mod-builder portable compiler"
LABEL org.opencontainers.image.description="Horizon native-build environment targeting glibc 2.35"
