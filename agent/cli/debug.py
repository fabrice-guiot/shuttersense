"""
Debug CLI commands for ShutterSense agent diagnostics.

NOT included in production builds. Requires SHUTTERSENSE_DEBUG_COMMANDS=1
environment variable to be available in development mode.

Usage:
    SHUTTERSENSE_DEBUG_COMMANDS=1 shuttersense-agent debug compare-inventory con_xxx
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import unquote

import click

from src.api_client import AgentApiClient
from src.config import AgentConfig
from src.credential_store import CredentialStore

logger = logging.getLogger("shuttersense.agent.cli.debug")


# ============================================================================
# Helpers
# ============================================================================


def _get_api_client() -> Optional[AgentApiClient]:
    """Get configured API client or None if not registered."""
    config = AgentConfig()
    if not config.api_key:
        return None
    return AgentApiClient(
        server_url=config.server_url,
        api_key=config.api_key,
    )


def _create_storage_adapter(connector_type: str, credentials: dict):
    """
    Create storage adapter for cloud access.

    Args:
        connector_type: Connector type (s3, gcs)
        credentials: Credentials dictionary

    Returns:
        S3Adapter or GCSAdapter instance
    """
    if connector_type == "s3":
        from src.remote import S3Adapter
        return S3Adapter(credentials)
    elif connector_type == "gcs":
        from src.remote import GCSAdapter
        return GCSAdapter(credentials)
    else:
        raise ValueError(f"Unsupported connector type for inventory: {connector_type}")


def _fetch_object(adapter, bucket: str, key: str, connector_type: str) -> bytes:
    """Fetch an object from cloud storage."""
    if connector_type == "s3":
        response = adapter.client.get_object(Bucket=bucket, Key=key)
        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()
    elif connector_type == "gcs":
        blob = adapter.bucket.blob(key)
        return blob.download_as_bytes()
    else:
        raise ValueError(f"Unsupported connector type: {connector_type}")


def _build_manifest_location(inventory_config: dict, connector_type: str) -> Tuple[str, str]:
    """
    Build the inventory manifest search location.

    Returns:
        Tuple of (destination_bucket, search_location)
    """
    if connector_type == "s3":
        destination_bucket = inventory_config.get("destination_bucket", "")
        destination_prefix = inventory_config.get("destination_prefix", "").strip("/")
        source_bucket = inventory_config.get("source_bucket", "")
        config_name = inventory_config.get("config_name", "")

        if not destination_bucket or not source_bucket or not config_name:
            raise ValueError("Missing required S3 inventory configuration fields")

        if destination_prefix:
            inventory_prefix = f"{destination_prefix}/{source_bucket}/{config_name}/"
        else:
            inventory_prefix = f"{source_bucket}/{config_name}/"

        return destination_bucket, f"{destination_bucket}/{inventory_prefix}"

    elif connector_type == "gcs":
        destination_bucket = inventory_config.get("destination_bucket", "")
        report_config_name = inventory_config.get("report_config_name", "")

        if not destination_bucket or not report_config_name:
            raise ValueError("Missing required GCS inventory configuration fields")

        return destination_bucket, f"{destination_bucket}/{report_config_name}/"

    else:
        raise ValueError(f"Unsupported connector type: {connector_type}")


def _discover_manifests(adapter, location: str) -> List[str]:
    """Discover all manifest files at the inventory location, sorted newest first."""
    files = adapter.list_files(location)
    return sorted(
        [f for f in files if f.endswith("manifest.json")],
        reverse=True,
    )


def _parse_manifest_entries(
    adapter,
    manifest_key: str,
    destination_bucket: str,
    connector_type: str,
) -> List:
    """
    Fetch and parse a manifest, returning all InventoryEntry objects.

    Args:
        adapter: Storage adapter
        manifest_key: Full key to manifest.json
        destination_bucket: Bucket containing data files
        connector_type: s3 or gcs

    Returns:
        List of InventoryEntry objects
    """
    from src.analysis.inventory_parser import (
        parse_s3_manifest,
        parse_s3_csv_stream,
        parse_gcs_manifest,
        parse_gcs_csv_stream,
        parse_parquet_stream,
        InventoryEntry,
    )

    manifest_content = _fetch_object(adapter, destination_bucket, manifest_key, connector_type)

    all_entries: List[InventoryEntry] = []

    if connector_type == "s3":
        manifest = parse_s3_manifest(manifest_content.decode("utf-8"))
        click.echo(f"  Format: {manifest.file_format}, data files: {len(manifest.files)}")

        for idx, file_ref in enumerate(manifest.files):
            click.echo(f"  Parsing data file {idx + 1}/{len(manifest.files)}...")
            data = _fetch_object(adapter, destination_bucket, file_ref.key, connector_type)

            if manifest.file_format.upper() == "PARQUET":
                entries = list(parse_parquet_stream(data, provider="s3"))
            else:
                entries = list(parse_s3_csv_stream(data, manifest.schema_fields))

            all_entries.extend(entries)

    elif connector_type == "gcs":
        manifest = parse_gcs_manifest(manifest_content.decode("utf-8"))
        click.echo(f"  Shards: {manifest.shard_count}")

        manifest_dir = "/".join(manifest_key.split("/")[:-1])

        for idx, shard_name in enumerate(manifest.shard_file_names):
            click.echo(f"  Parsing shard {idx + 1}/{manifest.shard_count}...")
            shard_key = f"{manifest_dir}/{shard_name}" if manifest_dir else shard_name
            data = _fetch_object(adapter, destination_bucket, shard_key, connector_type)

            if shard_name.endswith(".parquet"):
                entries = list(parse_parquet_stream(data, provider="gcs"))
            else:
                entries = list(parse_gcs_csv_stream(data))

            all_entries.extend(entries)

    return all_entries


def _filter_entries_by_prefix(entries: List, folder_path: str) -> List:
    """Filter inventory entries by folder path prefix."""
    prefix = folder_path if folder_path.endswith("/") else folder_path + "/"
    return [entry for entry in entries if entry.key.startswith(prefix)]


def _convert_cached_file_info(cached_file_info: List[dict], collection_path: str) -> List:
    """
    Convert cached FileInfo from server format to adapter FileInfo format.

    Replicates the same transformation as job_executor._convert_cached_file_info:
    URL-decodes keys and strips the collection path prefix to get relative paths.

    Args:
        cached_file_info: List of FileInfo dicts from server (key, size, last_modified, ...)
        collection_path: Collection location (used to extract relative paths)

    Returns:
        List of FileInfo objects with relative paths
    """
    from src.remote.base import FileInfo

    file_infos: List[FileInfo] = []

    # Normalize collection path (remove trailing slash for prefix matching)
    # Also URL-decode the collection path for consistent matching
    prefix = unquote(collection_path.rstrip("/") + "/") if collection_path else ""

    for fi in cached_file_info:
        key = fi.get("key", "")
        if not key:
            continue

        # URL-decode the key (S3/GCS inventory keys are URL-encoded)
        decoded_key = unquote(key)

        # Extract relative path by removing collection prefix
        if prefix and decoded_key.startswith(prefix):
            relative_path = decoded_key[len(prefix):]
        else:
            # If key doesn't match prefix, use full decoded key
            relative_path = decoded_key

        file_infos.append(FileInfo(
            path=relative_path,
            size=fi.get("size", 0),
            last_modified=fi.get("last_modified"),
        ))

    return file_infos


def _entries_to_file_info_with_transform(entries: List, collection_path: str) -> List:
    """
    Convert InventoryEntry objects to FileInfo objects, applying the same
    transformation as _convert_cached_file_info (URL-decode + strip prefix).

    This ensures manifest-derived hashes match stored-FileInfo-derived hashes.

    Args:
        entries: List of InventoryEntry objects
        collection_path: Collection location (used to extract relative paths)

    Returns:
        List of FileInfo objects with relative paths
    """
    from src.remote.base import FileInfo

    prefix = unquote(collection_path.rstrip("/") + "/") if collection_path else ""

    file_infos: List[FileInfo] = []
    for entry in entries:
        decoded_key = unquote(entry.key)

        if prefix and decoded_key.startswith(prefix):
            relative_path = decoded_key[len(prefix):]
        else:
            relative_path = decoded_key

        file_infos.append(FileInfo(
            path=relative_path,
            size=entry.size,
            last_modified=entry.last_modified or "",
        ))

    return file_infos


def _entries_to_file_info(entries: List) -> List:
    """Convert InventoryEntry objects to FileInfo objects (raw keys, no transformation)."""
    from src.remote.base import FileInfo

    return [
        FileInfo(
            path=entry.key,
            size=entry.size,
            last_modified=entry.last_modified or "",
        )
        for entry in entries
    ]


def _compute_hash_from_file_info(file_infos: List) -> Tuple[str, int]:
    """Compute Input State file list hash from FileInfo objects."""
    from src.input_state import InputStateComputer

    computer = InputStateComputer()
    return computer.compute_file_list_hash_from_file_info(file_infos)


def _diff_entries(entries_a: List, entries_b: List) -> Tuple[List, List, List]:
    """
    Compute diff between two sets of InventoryEntry objects.

    Args:
        entries_a: Newer manifest entries
        entries_b: Older manifest entries

    Returns:
        Tuple of (added, removed, changed) where:
        - added: entries in A but not B
        - removed: entries in B but not A
        - changed: list of (entry_a, entry_b) tuples for entries present in both
          but with different size, last_modified, or etag
    """
    map_a = {e.key: e for e in entries_a}
    map_b = {e.key: e for e in entries_b}

    added = []
    removed = []
    changed = []

    for key, entry_a in map_a.items():
        if key not in map_b:
            added.append(entry_a)
        else:
            entry_b = map_b[key]
            if (entry_a.size != entry_b.size or
                    entry_a.last_modified != entry_b.last_modified or
                    entry_a.etag != entry_b.etag):
                changed.append((entry_a, entry_b))

    for key in map_b:
        if key not in map_a:
            removed.append(map_b[key])

    return added, removed, changed


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _manifest_display_name(key: str) -> str:
    """Extract display name from manifest key (last 2 path segments)."""
    parts = key.split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else key


def _file_infos_to_hash_input_lines(file_infos: List) -> List[str]:
    """
    Convert FileInfo objects to the exact canonical lines used by _compute_file_list_hash.

    Each line is "path|size|mtime" where mtime is the integer timestamp.
    Lines are sorted by path (same ordering as the hash function).
    """
    from datetime import datetime as _dt

    tuples = []
    for info in file_infos:
        mtime = 0
        if info.last_modified:
            try:
                dt = _dt.fromisoformat(info.last_modified.replace("Z", "+00:00"))
                mtime = int(dt.timestamp())
            except (ValueError, AttributeError):
                pass
        tuples.append((info.path, info.size, mtime))

    tuples.sort(key=lambda f: f[0])
    return [f"{path}|{size}|{mtime}" for path, size, mtime in tuples]


def _write_dump_file(
    *,
    collection_guid: str,
    collection_name: str,
    collection_location: str,
    folder_path: str,
    connector_guid: str,
    connector_name: str,
    connector_type: str,
    tool: str,
    manifest_a_key: str,
    manifest_b_key: str,
    file_infos_a: List,
    file_infos_b: List,
    file_hash_a: str,
    file_hash_b: str,
    stored_file_infos: Optional[List],
    stored_file_hash: Optional[str],
    config_data: dict,
    config_hash: str,
    input_hash_a: str,
    input_hash_b: str,
    stored_input_hash: Optional[str],
    prev_result: Optional[dict],
) -> str:
    """
    Write a detailed Markdown dump file with all intermediate hash computation data.

    Returns:
        Path to the written file.
    """
    from datetime import timezone
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d_%H-%M-%S")

    # Sanitize collection GUID for filename (keep just the identifier part)
    col_short = collection_guid.replace("col_", "")[:12]
    filename = f"debug-dump_{col_short}_{tool}_{date_str}.md"

    lines: List[str] = []

    def w(text: str = "") -> None:
        lines.append(text)

    # --- Header ---
    w("# Debug Dump: Inventory Hash Comparison")
    w()
    w(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    w(f"**Collection:** `{collection_guid}` ({collection_name})")
    w(f"**Location:** `{collection_location}`")
    w(f"**Folder path:** `{folder_path}`")
    w(f"**Connector:** `{connector_guid}` ({connector_name}, {connector_type.upper()})")
    w(f"**Tool:** `{tool}`")
    w()

    # --- Summary ---
    w("## Summary")
    w()
    w("| Source | File List Hash | Input State Hash |")
    w("|--------|---------------|-----------------|")
    w(f"| Manifest A (newer) | `{file_hash_a}` | `{input_hash_a}` |")
    w(f"| Manifest B (older) | `{file_hash_b}` | `{input_hash_b}` |")
    if stored_file_hash and stored_input_hash:
        w(f"| Stored FileInfo | `{stored_file_hash}` | `{stored_input_hash}` |")
    if prev_result:
        w(f"| Previous Result | — | `{prev_result.get('input_state_hash', 'N/A')}` |")
    w()

    manifest_a_match_b = "YES" if file_hash_a == file_hash_b else "NO"
    w(f"**Manifest A == Manifest B:** {manifest_a_match_b}")
    if stored_file_hash:
        w(f"**Stored == Manifest A:** {'YES' if stored_file_hash == file_hash_a else 'NO'}")
        w(f"**Stored == Manifest B:** {'YES' if stored_file_hash == file_hash_b else 'NO'}")
    if prev_result:
        prev_hash = prev_result.get("input_state_hash", "")
        w(f"**Previous Result == Stored:** {'YES' if stored_input_hash and prev_hash == stored_input_hash else 'NO'}")
        w(f"**Previous Result == Manifest A:** {'YES' if prev_hash == input_hash_a else 'NO'}")
        w(f"**Previous Result == Manifest B:** {'YES' if prev_hash == input_hash_b else 'NO'}")
    w()

    # --- Configuration ---
    w("## Configuration Hash")
    w()
    w(f"**Config hash:** `{config_hash}`")
    w()
    w("```json")
    # Show only the relevant keys that _extract_relevant_config would pick
    relevant_keys = ["photo_extensions", "metadata_extensions", "require_sidecar",
                     "cameras", "processing_methods", "pipeline"]
    relevant = {k: config_data[k] for k in relevant_keys if k in config_data}
    w(json.dumps(relevant, sort_keys=True, indent=2))
    w("```")
    w()

    # --- Manifest details ---
    w("## Manifests")
    w()
    w(f"**Manifest A (newer):** `{manifest_a_key}`")
    w(f"**Manifest B (older):** `{manifest_b_key}`")
    w()

    # --- Hash input for each source ---
    hash_input_a = _file_infos_to_hash_input_lines(file_infos_a)
    hash_input_b = _file_infos_to_hash_input_lines(file_infos_b)

    w(f"## File List Hash Input — Manifest A ({len(hash_input_a):,} entries)")
    w()
    w(f"**Hash:** `{file_hash_a}`")
    w()
    w("Each line is `path|size|mtime_timestamp` (sorted by path).")
    w()
    w("```")
    for line in hash_input_a:
        w(line)
    w("```")
    w()

    w(f"## File List Hash Input — Manifest B ({len(hash_input_b):,} entries)")
    w()
    w(f"**Hash:** `{file_hash_b}`")
    w()
    w("```")
    for line in hash_input_b:
        w(line)
    w("```")
    w()

    if stored_file_infos is not None:
        hash_input_stored = _file_infos_to_hash_input_lines(stored_file_infos)
        w(f"## File List Hash Input — Stored FileInfo ({len(hash_input_stored):,} entries)")
        w()
        w(f"**Hash:** `{stored_file_hash}`")
        w()
        w("```")
        for line in hash_input_stored:
            w(line)
        w("```")
        w()

    # --- Previous result ---
    if prev_result:
        w("## Previous Result")
        w()
        w(f"**GUID:** `{prev_result.get('guid', 'N/A')}`")
        w(f"**Input State Hash:** `{prev_result.get('input_state_hash', 'N/A')}`")
        w(f"**Completed at:** {prev_result.get('completed_at', 'N/A')}")
        w()

    # --- Input State Hash formula ---
    w("## Input State Hash Formula")
    w()
    w("```")
    w("SHA256(\"...|{file_list_hash}|{config_hash}\")")
    w("")
    w(f"Manifest A: SHA256(\"{tool}|{file_hash_a}|{config_hash}\") = {input_hash_a}")
    w(f"Manifest B: SHA256(\"{tool}|{file_hash_b}|{config_hash}\") = {input_hash_b}")
    if stored_file_hash and stored_input_hash:
        w(f"Stored:     SHA256(\"{tool}|{stored_file_hash}|{config_hash}\") = {stored_input_hash}")
    w("```")
    w()

    content = "\n".join(lines)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return filename


# ============================================================================
# CLI Commands
# ============================================================================


@click.group("debug")
def debug():
    """Debug and diagnostic commands (development only).

    These commands are NOT available in production builds.
    They help diagnose issues with inventory processing and
    Input State hash computation.

    Requires SHUTTERSENSE_DEBUG_COMMANDS=1 environment variable.
    """
    pass


@debug.command("compare-inventory")
@click.argument("connector_guid")
@click.option("--collection", default=None,
              help="Collection GUID (col_xxx) — compute hashes matching tool execution for this collection")
@click.option("--list-folders", is_flag=True, help="List available folders from the latest manifest and exit")
@click.option("--tool", default=None, type=click.Choice(["photostats", "photo_pairing", "pipeline_validation"]),
              help="Compute full Input State hash for this tool (includes team config)")
@click.option("--dump", is_flag=True, help="Write a detailed Markdown dump of all intermediate hash data (requires --collection and --tool)")
@click.option("--limit", default=50, help="Max number of diff entries to show (default: 50)")
@click.option("--show-all", is_flag=True, help="Show all differences (no limit)")
@click.option("--verbose", is_flag=True, help="Show full details for each difference")
def compare_inventory(
    connector_guid: str,
    collection: Optional[str],
    list_folders: bool,
    tool: Optional[str],
    dump: bool,
    limit: int,
    show_all: bool,
    verbose: bool,
):
    """Compare FileInfo from the two most recent inventory manifests.

    Fetches the two most recent inventory manifests for the given connector,
    parses them, extracts FileInfo, and shows a diff. Also computes and
    compares Input State hashes to help diagnose why hashes change between
    inventory import runs.

    When --collection is specified, uses the collection's stored FileInfo and
    location to compute hashes that exactly match what tool execution produces.

    CONNECTOR_GUID is the connector identifier (e.g., con_01abc123...).
    """
    # 0. Validate --dump prerequisites
    if dump and (not collection or not tool):
        click.echo(
            "Error: --dump requires both --collection and --tool to be specified.",
            err=True,
        )
        raise SystemExit(1)

    # 1. Check registration and get API client
    client = _get_api_client()
    if not client:
        click.echo("Error: Agent not registered. Run 'shuttersense-agent register' first.", err=True)
        raise SystemExit(1)

    # 2. Fetch connector debug info from server
    click.echo(f"Fetching connector info for {connector_guid}...")
    try:
        response = client.get(f"/connectors/{connector_guid}/debug-info")
        if response.status_code == 404:
            click.echo(f"Error: Connector not found: {connector_guid}", err=True)
            raise SystemExit(1)
        elif response.status_code != 200:
            click.echo(f"Error: Failed to fetch connector info (HTTP {response.status_code})", err=True)
            raise SystemExit(1)

        connector_info = response.json()
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    connector_name = connector_info["name"]
    connector_type = connector_info["type"]
    credential_location = connector_info["credential_location"]
    inventory_config = connector_info.get("inventory_config")

    if not inventory_config:
        click.echo(f"Error: Connector {connector_guid} does not have inventory configuration.", err=True)
        raise SystemExit(1)

    # 3. If --collection specified, fetch collection debug info and validate
    collection_info = None
    if collection:
        click.echo(f"Fetching collection info for {collection}...")
        try:
            col_response = client.get(f"/collections/{collection}/debug-info")
            if col_response.status_code == 404:
                click.echo(f"Error: Collection not found: {collection}", err=True)
                raise SystemExit(1)
            elif col_response.status_code != 200:
                click.echo(f"Error: Failed to fetch collection info (HTTP {col_response.status_code})", err=True)
                raise SystemExit(1)

            collection_info = col_response.json()
        except SystemExit:
            raise
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        # Validate collection is linked to this connector
        if collection_info.get("connector_guid") != connector_guid:
            click.echo(
                f"Error: Collection {collection} is not linked to connector {connector_guid}.\n"
                f"  Collection's connector: {collection_info.get('connector_guid', 'none')}",
                err=True,
            )
            raise SystemExit(1)

        if not collection_info.get("folder_path"):
            click.echo(
                f"Error: Collection {collection} has no inventory folder mapping.",
                err=True,
            )
            raise SystemExit(1)

    # 4. Get credentials
    if credential_location == "agent":
        store = CredentialStore()
        credentials = store.get_credentials(connector_guid)
        if not credentials:
            click.echo(
                f"Error: No local credentials found for connector {connector_guid}. "
                "Run 'shuttersense-agent connectors configure' to set up credentials.",
                err=True,
            )
            raise SystemExit(1)
    else:
        click.echo(
            f"Error: Connector credentials are stored on the server ({credential_location}). "
            "This debug command only supports agent-side credentials.",
            err=True,
        )
        raise SystemExit(1)

    # 5. Create storage adapter
    try:
        adapter = _create_storage_adapter(connector_type, credentials)
    except Exception as e:
        click.echo(f"Error creating storage adapter: {e}", err=True)
        raise SystemExit(1)

    # 6. Print header
    click.echo()
    click.echo("=== Inventory Manifest Comparison ===")
    click.echo(f"Connector: {connector_guid} ({connector_name})")
    click.echo(f"Type: {connector_type.upper()}")
    if collection_info:
        click.echo(f"Collection: {collection} ({collection_info['name']})")
        click.echo(f"  Location: {collection_info['location']}")
        click.echo(f"  Folder path: {collection_info['folder_path']}")
        click.echo(f"  FileInfo source: {collection_info.get('file_info_source', 'none')}")
        stored_count = len(collection_info.get("file_info") or [])
        click.echo(f"  Stored FileInfo entries: {stored_count:,}")
    click.echo()

    # 7. Discover manifests
    try:
        destination_bucket, location = _build_manifest_location(inventory_config, connector_type)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"Searching for manifests at: {location}")
    try:
        manifest_keys = _discover_manifests(adapter, location)
    except Exception as e:
        click.echo(f"Error discovering manifests: {e}", err=True)
        raise SystemExit(1)

    if not manifest_keys:
        click.echo(f"Error: No manifest.json files found at {location}", err=True)
        raise SystemExit(1)

    click.echo(f"Found {len(manifest_keys)} manifest(s)")
    click.echo()

    # --list-folders: parse latest manifest, show folders, and exit
    if list_folders:
        click.echo(f"Parsing latest manifest: {_manifest_display_name(manifest_keys[0])}")
        try:
            entries = _parse_manifest_entries(adapter, manifest_keys[0], destination_bucket, connector_type)
        except Exception as e:
            click.echo(f"Error parsing manifest: {e}", err=True)
            raise SystemExit(1)

        from src.analysis.inventory_parser import extract_folders
        folders_set = extract_folders(entry.key for entry in entries)
        sorted_folders = sorted(folders_set)

        click.echo()
        click.echo(f"=== Folders ({len(sorted_folders)}) ===")
        for f in sorted_folders:
            count = sum(1 for e in entries if e.key.startswith(f))
            click.echo(f"  {f}  ({count:,} files)")

        click.echo()
        click.echo("Use --collection <col_guid> to compare with a collection's stored FileInfo.")
        raise SystemExit(0)

    if len(manifest_keys) < 2:
        # Only one manifest — show summary
        click.echo("Only one manifest found. Cannot compare two manifests.")
        click.echo(f"Manifest: {_manifest_display_name(manifest_keys[0])}")
        click.echo()
        click.echo("Parsing manifest...")
        try:
            entries = _parse_manifest_entries(adapter, manifest_keys[0], destination_bucket, connector_type)
            if collection_info:
                folder_path = collection_info["folder_path"]
                entries = _filter_entries_by_prefix(entries, folder_path)
                click.echo(f"  (filtered to folder: {folder_path})")

            # Use transformed hash if collection context is available
            if collection_info:
                file_infos = _entries_to_file_info_with_transform(entries, collection_info["location"])
            else:
                file_infos = _entries_to_file_info(entries)
            hash_val, count = _compute_hash_from_file_info(file_infos)
            click.echo(f"  Entries: {count:,}")
            click.echo(f"  File list hash: {hash_val}")
        except Exception as e:
            click.echo(f"Error parsing manifest: {e}", err=True)
        raise SystemExit(0)

    # 8. Parse the two most recent manifests
    manifest_a_key = manifest_keys[0]  # newer
    manifest_b_key = manifest_keys[1]  # older

    click.echo(f"Manifest A (newer): {_manifest_display_name(manifest_a_key)}")
    try:
        entries_a = _parse_manifest_entries(adapter, manifest_a_key, destination_bucket, connector_type)
    except Exception as e:
        click.echo(f"Error parsing manifest A: {e}", err=True)
        raise SystemExit(1)

    click.echo()
    click.echo(f"Manifest B (older): {_manifest_display_name(manifest_b_key)}")
    try:
        entries_b = _parse_manifest_entries(adapter, manifest_b_key, destination_bucket, connector_type)
    except Exception as e:
        click.echo(f"Error parsing manifest B: {e}", err=True)
        raise SystemExit(1)

    # 9. Filter entries by collection folder path (or show all)
    folder_path = None
    if collection_info:
        folder_path = collection_info["folder_path"]
        click.echo()
        click.echo(f"Filtering to collection folder: {folder_path}")
        entries_a = _filter_entries_by_prefix(entries_a, folder_path)
        entries_b = _filter_entries_by_prefix(entries_b, folder_path)

    # 10. Entry counts
    click.echo()
    click.echo("=== Entry Counts ===")
    click.echo(f"  Manifest A: {len(entries_a):,} entries")
    click.echo(f"  Manifest B: {len(entries_b):,} entries")

    # 11. Compute and compare hashes
    from src.input_state import InputStateComputer
    computer = InputStateComputer()

    # Compute file list hashes using the same transformation as tool execution
    if collection_info:
        collection_location = collection_info["location"]
        file_infos_a = _entries_to_file_info_with_transform(entries_a, collection_location)
        file_infos_b = _entries_to_file_info_with_transform(entries_b, collection_location)
    else:
        file_infos_a = _entries_to_file_info(entries_a)
        file_infos_b = _entries_to_file_info(entries_b)

    file_hash_a, _ = _compute_hash_from_file_info(file_infos_a)
    file_hash_b, _ = _compute_hash_from_file_info(file_infos_b)

    click.echo()
    click.echo("=== File List Hashes (from manifests) ===")
    click.echo(f"  Manifest A: {file_hash_a}")
    click.echo(f"  Manifest B: {file_hash_b}")
    file_match = file_hash_a == file_hash_b
    click.echo(f"  Match: {'YES' if file_match else 'NO'}")

    # 12. If collection specified, also compute hash from stored FileInfo
    stored_file_hash = None
    stored_file_infos: Optional[List] = None
    if collection_info and collection_info.get("file_info"):
        stored_file_infos = _convert_cached_file_info(
            collection_info["file_info"],
            collection_info["location"],
        )
        stored_file_hash, stored_count = _compute_hash_from_file_info(stored_file_infos)

        click.echo()
        click.echo("=== File List Hash (from stored FileInfo) ===")
        click.echo(f"  Hash: {stored_file_hash}")
        click.echo(f"  Entries: {stored_count:,}")
        stored_matches_a = stored_file_hash == file_hash_a
        stored_matches_b = stored_file_hash == file_hash_b
        click.echo(f"  Matches Manifest A: {'YES' if stored_matches_a else 'NO'}")
        click.echo(f"  Matches Manifest B: {'YES' if stored_matches_b else 'NO'}")

    # 13. If --tool is specified, compute full Input State hash (file + config + tool)
    stored_input_hash: Optional[str] = None
    config_data: Optional[dict] = None
    config_hash: Optional[str] = None
    input_hash_a: Optional[str] = None
    input_hash_b: Optional[str] = None
    prev_result: Optional[dict] = None
    if tool:
        click.echo()
        click.echo(f"=== Input State Hashes (tool: {tool}) ===")
        try:
            team_config_response = client.get_team_config()
            config_data = team_config_response.get("config", {})
            # Include pipeline in config, matching ApiConfigLoader.load() behavior:
            # The job config path adds pipeline to the config dict before hashing.
            # _extract_relevant_config includes "pipeline" as a relevant key.
            default_pipeline = team_config_response.get("default_pipeline")
            if default_pipeline:
                config_data["pipeline"] = default_pipeline
            config_hash = computer.compute_configuration_hash(config_data)
            click.echo(f"  Config hash: {config_hash}")

            input_hash_a = computer.compute_input_state_hash(file_hash_a, config_hash, tool)
            input_hash_b = computer.compute_input_state_hash(file_hash_b, config_hash, tool)

            click.echo()
            click.echo(f"  From Manifest A: {input_hash_a}")
            click.echo(f"  From Manifest B: {input_hash_b}")
            input_match = input_hash_a == input_hash_b
            click.echo(f"  Match: {'YES' if input_match else 'NO'}")

            if stored_file_hash:
                stored_input_hash = computer.compute_input_state_hash(stored_file_hash, config_hash, tool)
                click.echo()
                click.echo(f"  From stored FileInfo: {stored_input_hash}")
                click.echo(f"  Matches Manifest A: {'YES' if stored_input_hash == input_hash_a else 'NO'}")
                click.echo(f"  Matches Manifest B: {'YES' if stored_input_hash == input_hash_b else 'NO'}")

            # Fetch previous result for comparison
            if collection:
                click.echo()
                try:
                    prev_result = client.get_previous_result(collection, tool)
                    if prev_result:
                        prev_hash = prev_result.get("input_state_hash", "")
                        click.echo(f"  Previous result hash: {prev_hash}")
                        click.echo(f"  Completed at: {prev_result.get('completed_at', 'unknown')}")
                        click.echo(f"  Result GUID: {prev_result.get('guid', 'unknown')}")

                        # Compare with all computed hashes
                        if stored_input_hash:
                            matches_stored = prev_hash == stored_input_hash
                            click.echo(f"  Matches stored FileInfo hash: {'YES' if matches_stored else 'NO'}")
                        matches_a = prev_hash == input_hash_a
                        matches_b = prev_hash == input_hash_b
                        click.echo(f"  Matches Manifest A hash: {'YES' if matches_a else 'NO'}")
                        click.echo(f"  Matches Manifest B hash: {'YES' if matches_b else 'NO'}")
                    else:
                        click.echo(f"  No previous result found for {tool} on {collection}")
                except Exception as e:
                    click.echo(f"  Could not fetch previous result: {e}")

        except Exception as e:
            click.echo(f"  Error fetching team config: {e}", err=True)
            click.echo("  Cannot compute full Input State hash without team config.")

    # 14. Write dump file if requested
    if dump and collection_info and collection and tool and config_data is not None and config_hash and input_hash_a and input_hash_b:
        dump_path = _write_dump_file(
            collection_guid=collection,
            collection_name=collection_info["name"],
            collection_location=collection_info["location"],
            folder_path=collection_info["folder_path"],
            connector_guid=connector_guid,
            connector_name=connector_name,
            connector_type=connector_type,
            tool=tool,
            manifest_a_key=_manifest_display_name(manifest_a_key),
            manifest_b_key=_manifest_display_name(manifest_b_key),
            file_infos_a=file_infos_a,
            file_infos_b=file_infos_b,
            file_hash_a=file_hash_a,
            file_hash_b=file_hash_b,
            stored_file_infos=stored_file_infos,
            stored_file_hash=stored_file_hash,
            config_data=config_data,
            config_hash=config_hash,
            input_hash_a=input_hash_a,
            input_hash_b=input_hash_b,
            stored_input_hash=stored_input_hash,
            prev_result=prev_result,
        )
        click.echo()
        click.echo(f"Dump written to: {dump_path}")

    if file_match:
        click.echo()
        click.echo("File list hashes match. No differences that affect Input State.")
        raise SystemExit(0)

    # 14. Compute diff
    added, removed, changed = _diff_entries(entries_a, entries_b)

    click.echo()
    click.echo("=== Differences ===")
    click.echo(f"  Added (in A, not in B): {len(added)}")
    click.echo(f"  Removed (in B, not in A): {len(removed)}")
    click.echo(f"  Changed (different size/mtime/etag): {len(changed)}")

    max_display = len(added) + len(removed) + len(changed) if show_all else limit
    displayed = 0

    # Changed entries (most interesting for hash diagnosis)
    if changed:
        click.echo()
        click.echo("--- Changed entries ---")
        for entry_a, entry_b in changed:
            if displayed >= max_display:
                remaining = len(changed) - displayed
                click.echo(f"  ... and {remaining} more changed entries (use --show-all)")
                break

            size_same = entry_a.size == entry_b.size
            mtime_same = entry_a.last_modified == entry_b.last_modified
            etag_same = entry_a.etag == entry_b.etag

            if verbose:
                click.echo(f"  ~ {entry_a.key}")
                click.echo(f"    size: {entry_b.size:,} -> {entry_a.size:,}  ({'same' if size_same else 'CHANGED'})")
                click.echo(
                    f"    mtime: \"{entry_b.last_modified}\" -> \"{entry_a.last_modified}\""
                    f"  ({'same' if mtime_same else 'CHANGED'})"
                )
                click.echo(
                    f"    etag: \"{entry_b.etag}\" -> \"{entry_a.etag}\""
                    f"  ({'same' if etag_same else 'CHANGED'})"
                )
                if hasattr(entry_a, 'storage_class'):
                    click.echo(f"    storage_class: \"{entry_b.storage_class}\" -> \"{entry_a.storage_class}\"")
            else:
                # Compact: show key + what changed
                changes = []
                if not size_same:
                    changes.append("size")
                if not mtime_same:
                    changes.append("mtime")
                if not etag_same:
                    changes.append("etag")
                click.echo(f"  ~ {entry_a.key}  ({', '.join(changes)} changed)")

            displayed += 1

    # Added entries
    if added and displayed < max_display:
        click.echo()
        click.echo("--- Added entries ---")
        for entry in added:
            if displayed >= max_display:
                remaining = len(added) - (displayed - len(changed))
                click.echo(f"  ... and {remaining} more added entries (use --show-all)")
                break

            click.echo(f"  + {entry.key} ({_format_size(entry.size)}, mtime={entry.last_modified})")
            displayed += 1

    # Removed entries
    if removed and displayed < max_display:
        click.echo()
        click.echo("--- Removed entries ---")
        for entry in removed:
            if displayed >= max_display:
                remaining = len(removed) - (displayed - len(changed) - len(added))
                click.echo(f"  ... and {remaining} more removed entries (use --show-all)")
                break

            click.echo(f"  - {entry.key} ({_format_size(entry.size)}, mtime={entry.last_modified})")
            displayed += 1

    # 15. Diagnosis summary
    if not added and not removed and changed:
        # All differences are in changed entries — analyze patterns
        size_changes = sum(1 for a, b in changed if a.size != b.size)
        mtime_changes = sum(1 for a, b in changed if a.last_modified != b.last_modified)
        etag_changes = sum(1 for a, b in changed if a.etag != b.etag)

        click.echo()
        click.echo("=== Hash Diagnosis ===")
        click.echo("  No entries were added or removed.")
        click.echo(f"  {len(changed)} entries have differences:")
        if size_changes:
            click.echo(f"    - {size_changes} with size changes")
        if mtime_changes:
            click.echo(f"    - {mtime_changes} with mtime changes")
        if etag_changes:
            click.echo(f"    - {etag_changes} with etag changes (not used in hash)")
        if mtime_changes and not size_changes:
            click.echo("  The Input State hash changed due to mtime differences only.")
            click.echo("  This may indicate timestamp precision differences between inventory reports.")
