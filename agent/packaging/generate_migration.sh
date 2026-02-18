#!/bin/bash
# Generate an Alembic migration for a release manifest entry.
#
# This script is called by platform build scripts after a successful build.
# It fills in the release_migration.py.template with build parameters and
# writes a new migration file to backend/src/db/migrations/versions/.
#
# Usage:
#   generate_migration.sh --version VERSION --platform PLATFORM \
#                         --checksum CHECKSUM --filename FILENAME \
#                         --file-size FILE_SIZE
#
# Example:
#   generate_migration.sh --version v1.2.3 --platform darwin-arm64 \
#                         --checksum abc123...def --filename shuttersense-agent-darwin-arm64 \
#                         --file-size 52428800

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$AGENT_DIR")"
MIGRATIONS_DIR="$PROJECT_ROOT/backend/src/db/migrations/versions"
TEMPLATE_FILE="$SCRIPT_DIR/templates/release_migration.py.template"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
VERSION=""
PLATFORM=""
CHECKSUM=""
FILENAME=""
FILE_SIZE="0"

while [[ $# -gt 0 ]]; do
    case $1 in
        --version)   VERSION="$2";   shift 2 ;;
        --platform)  PLATFORM="$2";  shift 2 ;;
        --checksum)  CHECKSUM="$2";  shift 2 ;;
        --filename)  FILENAME="$2";  shift 2 ;;
        --file-size) FILE_SIZE="$2"; shift 2 ;;
        *)
            echo "Error: Unknown argument: $1"
            echo "Usage: generate_migration.sh --version VERSION --platform PLATFORM \\"
            echo "         --checksum CHECKSUM --filename FILENAME --file-size FILE_SIZE"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Validate required arguments
# ---------------------------------------------------------------------------
missing=()
[ -z "$VERSION" ]  && missing+=("--version")
[ -z "$PLATFORM" ] && missing+=("--platform")
[ -z "$CHECKSUM" ] && missing+=("--checksum")
[ -z "$FILENAME" ] && missing+=("--filename")

if [ ${#missing[@]} -gt 0 ]; then
    echo "Error: Missing required arguments: ${missing[*]}"
    exit 1
fi

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template file not found: $TEMPLATE_FILE"
    exit 1
fi

if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "Error: Migrations directory not found: $MIGRATIONS_DIR"
    exit 1
fi

# ---------------------------------------------------------------------------
# Determine the next migration number and current head revision
# ---------------------------------------------------------------------------
# Find the highest existing migration number prefix (NNN_*.py)
MAX_NUM=0
for f in "$MIGRATIONS_DIR"/[0-9]*.py; do
    [ -f "$f" ] || continue
    basename_f=$(basename "$f")
    # Extract leading digits
    num="${basename_f%%_*}"
    # Remove leading zeros for arithmetic
    num_int=$((10#$num))
    if [ "$num_int" -gt "$MAX_NUM" ]; then
        MAX_NUM=$num_int
    fi
done

NEXT_NUM=$((MAX_NUM + 1))
# Zero-pad to 3 digits
NEXT_NUM_PADDED=$(printf "%03d" "$NEXT_NUM")

# The current head revision ID is the highest-numbered migration's revision ID.
# Convention in this project: revision = 'NNN_description'
# Find the file with the highest number prefix and extract its revision.
HEAD_FILE=""
for f in "$MIGRATIONS_DIR"/[0-9]*.py; do
    [ -f "$f" ] || continue
    basename_f=$(basename "$f")
    num="${basename_f%%_*}"
    num_int=$((10#$num))
    if [ "$num_int" -eq "$MAX_NUM" ]; then
        HEAD_FILE="$f"
    fi
done

if [ -z "$HEAD_FILE" ]; then
    echo "Error: Could not find current head migration in $MIGRATIONS_DIR"
    exit 1
fi

# Extract the revision string from the head file (e.g., revision = '068_fix_cameras_uuid_type')
DOWN_REVISION=$(grep -m1 "^revision = " "$HEAD_FILE" | sed "s/^revision = '//" | sed "s/'$//")
if [ -z "$DOWN_REVISION" ]; then
    echo "Error: Could not extract revision ID from $HEAD_FILE"
    exit 1
fi

# ---------------------------------------------------------------------------
# Build the migration file
# ---------------------------------------------------------------------------
# Clean platform string for filename (replace hyphens with underscores)
PLATFORM_CLEAN=$(echo "$PLATFORM" | tr '-' '_')

# Clean version string for filename (strip 'v' prefix, replace dots/hyphens/plus with underscores)
VERSION_CLEAN=$(echo "$VERSION" | sed 's/^v//' | tr '.-+' '___')

REVISION_ID="${NEXT_NUM_PADDED}_release_${VERSION_CLEAN}_${PLATFORM_CLEAN}"
CREATE_DATE=$(date +%Y-%m-%d)

# Generate a UUIDv4 for the manifest (cross-platform)
if command -v python3 &> /dev/null; then
    MANIFEST_UUID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
elif command -v uuidgen &> /dev/null; then
    MANIFEST_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
else
    echo "Error: No UUID generator available (need python3 or uuidgen)"
    exit 1
fi

OUTPUT_FILE="$MIGRATIONS_DIR/${REVISION_ID}.py"

echo "Generating release migration..."
echo "  Revision: $REVISION_ID"
echo "  Down revision: $DOWN_REVISION"
echo "  Version: $VERSION"
echo "  Platform: $PLATFORM"
echo "  Checksum: ${CHECKSUM:0:16}..."
echo "  Filename: $FILENAME"
echo "  File size: $FILE_SIZE"
echo "  UUID: $MANIFEST_UUID"

# Perform template substitution
sed \
    -e "s|\${REVISION_ID}|${REVISION_ID}|g" \
    -e "s|\${DOWN_REVISION}|${DOWN_REVISION}|g" \
    -e "s|\${CREATE_DATE}|${CREATE_DATE}|g" \
    -e "s|\${MANIFEST_UUID}|${MANIFEST_UUID}|g" \
    -e "s|\${VERSION}|${VERSION}|g" \
    -e "s|\${PLATFORM}|${PLATFORM}|g" \
    -e "s|\${CHECKSUM}|${CHECKSUM}|g" \
    -e "s|\${FILENAME}|${FILENAME}|g" \
    -e "s|\${FILE_SIZE}|${FILE_SIZE}|g" \
    "$TEMPLATE_FILE" > "$OUTPUT_FILE"

echo ""
echo "Migration generated: $OUTPUT_FILE"
echo ""
