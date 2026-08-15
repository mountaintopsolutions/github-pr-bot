#!/bin/bash

# GitHub PR Bot - Build and Push Script
# Builds multi-platform Docker image and pushes to GitHub Container Registry

set -e

# Configuration
# Derived from the repository so a fork publishes to its own registry namespace rather than
# failing to push to upstream's. Override with IMAGE_NAME to publish somewhere else.
# GHCR requires a lowercase path, while GitHub owner/repo names may not be.
if [ -z "${IMAGE_NAME:-}" ]; then
    REPO_PATH="${GITHUB_REPOSITORY:-}"
    if [ -z "$REPO_PATH" ]; then
        # local run: fall back to the origin remote. Parameter expansion rather than a regex, so
        # this behaves the same under BSD and GNU tooling, for every remote URL form:
        #   git@github.com:owner/repo.git, https://host/owner/repo.git, ssh://git@host/owner/repo
        ORIGIN_URL=$(git config --get remote.origin.url || true)
        ORIGIN_URL="${ORIGIN_URL%.git}"
        ORIGIN_URL="${ORIGIN_URL%/}"
        if [ -n "$ORIGIN_URL" ]; then
            REPO_NAME="${ORIGIN_URL##*/}"
            OWNER_PART="${ORIGIN_URL%/*}"
            OWNER="${OWNER_PART##*[:/]}"
            [ -n "$OWNER" ] && [ -n "$REPO_NAME" ] && REPO_PATH="$OWNER/$REPO_NAME"
        fi
    fi
    if [ -z "$REPO_PATH" ]; then
        echo "❌ Cannot determine the image name: set IMAGE_NAME or GITHUB_REPOSITORY" >&2
        exit 1
    fi
    IMAGE_NAME="ghcr.io/$(echo "$REPO_PATH" | tr '[:upper:]' '[:lower:]')"
fi
DOCKERFILE="Dockerfile.github_action"

echo "📦 Image: $IMAGE_NAME"

# Parse MAJOR/MINOR/PATCH out of a version string, ignoring any leading 'v' and pre-release suffix
parse_semver() {
    local core="${1#v}"
    core="${core%%-*}"
    if [[ $core =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
        MAJOR="${BASH_REMATCH[1]}"; MINOR="${BASH_REMATCH[2]}"; PATCH="${BASH_REMATCH[3]}"
    elif [[ $core =~ ^([0-9]+)\.([0-9]+)$ ]]; then
        MAJOR="${BASH_REMATCH[1]}"; MINOR="${BASH_REMATCH[2]}"; PATCH="0"
    elif [[ $core =~ ^([0-9]+)$ ]]; then
        MAJOR="${BASH_REMATCH[1]}"; MINOR="0"; PATCH="0"
    else
        echo "⚠️  Invalid version format: $1, using 1.0.0"
        MAJOR="1"; MINOR="0"; PATCH="0"
    fi
}

# An explicit VERSION wins; otherwise increment the highest existing tag.
RELEASE_VERSION="${VERSION:-}"
if [ -n "$RELEASE_VERSION" ]; then
    case "$RELEASE_VERSION" in v*) ;; *) RELEASE_VERSION="v$RELEASE_VERSION" ;; esac
    NEW_VERSION="$RELEASE_VERSION"
    parse_semver "$NEW_VERSION"
    echo "📌 Using explicit version: $NEW_VERSION"
    if git rev-parse "$NEW_VERSION" >/dev/null 2>&1; then
        echo "❌ Tag $NEW_VERSION already exists. Pick another VERSION, or delete the tag." >&2
        exit 1
    fi
else
    echo "🔍 Finding latest version tag..."
    LATEST_TAG=$(git tag -l 'v*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -n1)
    if [ -z "$LATEST_TAG" ]; then
        LATEST_TAG=$(git tag -l 'v*' | sort -V | tail -n1)
    fi
    if [ -z "$LATEST_TAG" ]; then
        LATEST_TAG="v1.0.0"
    fi
    echo "📌 Current version: $LATEST_TAG"

    parse_semver "$LATEST_TAG"
    NEW_PATCH=$((PATCH + 1))
    while git rev-parse "v${MAJOR}.${MINOR}.${NEW_PATCH}" >/dev/null 2>&1; do
        NEW_PATCH=$((NEW_PATCH + 1))
    done
    PATCH="$NEW_PATCH"
    NEW_VERSION="v${MAJOR}.${MINOR}.${PATCH}"
    echo "🔄 New version: $NEW_VERSION"
fi

# A pre-release - anything carrying a '-suffix', e.g. v1.0.12-dctest1 - publishes only its own tag.
# 'latest', 'vN' and 'vN.M' keep pointing at the last stable build, so a test image can never
# become what a caller pinned to a floating tag silently receives.
IS_PRERELEASE=false
case "$NEW_VERSION" in *-*) IS_PRERELEASE=true ;; esac

DOCKER_TAGS=("$IMAGE_NAME:$NEW_VERSION")
if [ "$IS_PRERELEASE" = true ]; then
    echo "🧪 Pre-release: publishing $NEW_VERSION only, leaving latest/v$MAJOR/v$MAJOR.$MINOR alone"
else
    DOCKER_TAGS+=("$IMAGE_NAME:latest" "$IMAGE_NAME:v$MAJOR" "$IMAGE_NAME:v$MAJOR.$MINOR")
fi

echo "🚀 Building GitHub PR Bot Docker image..."

# Create buildx builder if it doesn't exist
if ! docker buildx ls | grep -q "multiarch"; then
    echo "📦 Creating multi-platform builder..."
    docker buildx create --use --name multiarch --driver docker-container
fi

# Use the multiarch builder
docker buildx use multiarch

# Build and push multi-platform image with version tags
echo "🔨 Building and pushing multi-platform image..."
TAG_ARGS=()
for tag in "${DOCKER_TAGS[@]}"; do
    TAG_ARGS+=(--tag "$tag")
done
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --file "$DOCKERFILE" \
    "${TAG_ARGS[@]}" \
    --push \
    .

echo "✅ Successfully built and pushed:"
for tag in "${DOCKER_TAGS[@]}"; do
    echo "   - $tag"
done

# Create and push git tags
echo ""
echo "🏷️  Creating git tags..."
git tag -a "$NEW_VERSION" -m "Release $NEW_VERSION"
git push origin "$NEW_VERSION"
echo "   - $NEW_VERSION (new)"

if [ "$IS_PRERELEASE" = false ]; then
    git tag -fa "v$MAJOR" -m "Update major version tag to $NEW_VERSION"
    git push origin "v$MAJOR" --force
    git tag -fa "v$MAJOR.$MINOR" -m "Update minor version tag to $NEW_VERSION"
    git push origin "v$MAJOR.$MINOR" --force
    echo "   - v$MAJOR (updated)"
    echo "   - v$MAJOR.$MINOR (updated)"
fi

echo ""
echo "🎯 Image supports: linux/amd64, linux/arm64"
echo ""
ACTION_REF="${GITHUB_REPOSITORY:-${IMAGE_NAME#ghcr.io/}}"
echo "To use in GitHub Actions:"
echo "  uses: docker://$IMAGE_NAME:$NEW_VERSION"
echo "  uses: $ACTION_REF@$NEW_VERSION"
echo ""
echo "Note: 'uses: <repo>@<ref>' runs the image named in that ref's action.yaml, not the code at"
echo "that ref, so action.yaml has to name the tag published here - it is not updated for you."

# Output for GitHub Actions
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
        echo "new_version=$NEW_VERSION"
        echo "image_name=$IMAGE_NAME"
        echo "is_prerelease=$IS_PRERELEASE"
        echo "docker_tags<<GHA_EOF"
        for tag in "${DOCKER_TAGS[@]}"; do
            echo "- \`$tag\`"
        done
        echo "GHA_EOF"
    } >> "$GITHUB_OUTPUT"
fi 