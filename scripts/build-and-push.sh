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

# Get all version tags and find the highest one
echo "🔍 Finding latest version tag..."
LATEST_TAG=$(git tag -l 'v*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -n1)

# If no semantic version tags exist, check for any v* tags
if [ -z "$LATEST_TAG" ]; then
    LATEST_TAG=$(git tag -l 'v*' | sort -V | tail -n1)
fi

# If still no tags, use v1.0.0 as default
if [ -z "$LATEST_TAG" ]; then
    LATEST_TAG="v1.0.0"
fi

echo "📌 Current version: $LATEST_TAG"

# Parse version components
VERSION=${LATEST_TAG#v}

# Handle different version formats
if [[ $VERSION =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
elif [[ $VERSION =~ ^([0-9]+)\.([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="0"
elif [[ $VERSION =~ ^([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="0"
    PATCH="0"
else
    echo "⚠️  Invalid version format: $VERSION, using v1.0.0"
    MAJOR="1"
    MINOR="0"
    PATCH="0"
fi

# Increment patch version
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="v${MAJOR}.${MINOR}.${NEW_PATCH}"

# Check if new version already exists
if git rev-parse "$NEW_VERSION" >/dev/null 2>&1; then
    echo "⚠️  Tag $NEW_VERSION already exists, finding next available version..."
    while git rev-parse "v${MAJOR}.${MINOR}.${NEW_PATCH}" >/dev/null 2>&1; do
        NEW_PATCH=$((NEW_PATCH + 1))
    done
    NEW_VERSION="v${MAJOR}.${MINOR}.${NEW_PATCH}"
fi

echo "🔄 New version: $NEW_VERSION"

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
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --file $DOCKERFILE \
    --tag $IMAGE_NAME:latest \
    --tag $IMAGE_NAME:$NEW_VERSION \
    --tag $IMAGE_NAME:v$MAJOR.$MINOR \
    --tag $IMAGE_NAME:v$MAJOR \
    --push \
    .

echo "✅ Successfully built and pushed:"
echo "   - $IMAGE_NAME:latest"
echo "   - $IMAGE_NAME:$NEW_VERSION"
echo "   - $IMAGE_NAME:v$MAJOR.$MINOR"
echo "   - $IMAGE_NAME:v$MAJOR"

# Create and push git tags
echo ""
echo "🏷️  Creating git tags..."
git tag -a $NEW_VERSION -m "Release $NEW_VERSION"
git push origin $NEW_VERSION

# Update major and minor tags
git tag -fa v$MAJOR -m "Update major version tag to $NEW_VERSION"
git push origin v$MAJOR --force

git tag -fa v$MAJOR.$MINOR -m "Update minor version tag to $NEW_VERSION"
git push origin v$MAJOR.$MINOR --force

echo ""
echo "✅ Git tags updated:"
echo "   - $NEW_VERSION (new)"
echo "   - v$MAJOR (updated)"
echo "   - v$MAJOR.$MINOR (updated)"

echo ""
echo "🎯 Image supports: linux/amd64, linux/arm64"
echo ""
ACTION_REF="${GITHUB_REPOSITORY:-${IMAGE_NAME#ghcr.io/}}"
echo "To use in GitHub Actions:"
echo "  uses: docker://$IMAGE_NAME:latest"
echo "  uses: docker://$IMAGE_NAME:$NEW_VERSION"
echo "  uses: $ACTION_REF@$NEW_VERSION"
echo "  uses: $ACTION_REF@v$MAJOR"
echo ""
echo "Note: 'uses: <repo>@<ref>' runs the image named in that ref's action.yaml, not the code at"
echo "that ref, so action.yaml must point at $IMAGE_NAME for this to publish anything usable."

# Output for GitHub Actions
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "new_version=$NEW_VERSION" >> $GITHUB_OUTPUT
    echo "image_name=$IMAGE_NAME" >> $GITHUB_OUTPUT
fi 