"""
Formatting utilities for human-readable output.

Provides functions for formatting:
- Storage sizes (bytes → KB/MB/GB/TB)
- Other display formatting as needed
"""


def format_storage_bytes(bytes_value: int) -> str:
    """
    Convert bytes to human-readable storage string.

    Uses binary units (1 KB = 1024 bytes) with appropriate precision.

    Args:
        bytes_value: Storage size in bytes

    Returns:
        Human-readable string (e.g., "2.5 TB", "512 MB", "1.2 GB")

    Examples:
        >>> format_storage_bytes(0)
        '0 B'
        >>> format_storage_bytes(1024)
        '1.0 KB'
        >>> format_storage_bytes(1536)
        '1.5 KB'
        >>> format_storage_bytes(1048576)
        '1.0 MB'
        >>> format_storage_bytes(1073741824)
        '1.0 GB'
        >>> format_storage_bytes(2748779069440)
        '2.5 TB'
    """
    if bytes_value is None or bytes_value < 0:
        return "0 B"

    if bytes_value == 0:
        return "0 B"

    # Define units and their thresholds
    units = [
        (1024 ** 4, "TB"),
        (1024 ** 3, "GB"),
        (1024 ** 2, "MB"),
        (1024 ** 1, "KB"),
        (1, "B"),
    ]

    for threshold, unit in units:
        if bytes_value >= threshold:
            value = bytes_value / threshold
            # Use 1 decimal place for KB and above, no decimal for bytes
            if unit == "B":
                return f"{int(value)} B"
            else:
                return f"{value:.1f} {unit}"

    return "0 B"
