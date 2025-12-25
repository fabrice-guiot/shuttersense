# HTML Report Consistency Feature - Research & Decisions

Research document for best practices on Jinja2 templating, signal handling, and argparse help text patterns for the photo-admin CLI toolbox.

**Generated:** 2025-12-25
**Project:** photo-admin (Python 3.10+ CLI toolbox)
**Context:** Standardizing HTML report generation across PhotoStats and Photo Pairing tools

---

## 1. Jinja2 Template Best Practices

### Decision: Embedded Templates with Template Inheritance

**Selected Approach:**
- Use Jinja2 with embedded templates (no external template files)
- Implement base template + tool-specific extensions via template inheritance
- Define shared CSS/JS constants in a separate module for consistency
- Use Jinja2's built-in error handling with clear fallback messages

**Rationale:**

1. **Embedded vs External Templates:**
   - **Embedded chosen** because photo-admin tools are standalone CLI scripts
   - Each tool should be self-contained and runnable from any location
   - No need to manage template file paths or package data
   - Simplifies distribution and installation (single .py file per tool)
   - Current codebase already uses embedded HTML (see photo_stats.py:187-486, photo_pairing.py:473-787)

2. **Template Inheritance Pattern:**
   - Create a shared base template with common structure, CSS, and Chart.js setup
   - Tools extend base template and override specific blocks (title, content, scripts)
   - Eliminates code duplication while maintaining tool independence
   - Jinja2 syntax: `{% extends "base.html" %}` and `{% block content %}`

3. **CSS/JS Variable Management:**
   - Extract shared constants (colors, fonts, spacing) into a Python module: `utils/html_theme.py`
   - Define color palette, Chart.js color schemes, typography as Python dictionaries
   - Both tools import and use these constants in template generation
   - Ensures visual consistency across all reports
   - Easy to update theme in one place

4. **Error Handling:**
   - Jinja2 provides robust error handling via `Template.render()` try/except
   - Catch `jinja2.TemplateError` and subclasses (TemplateSyntaxError, UndefinedError)
   - Provide clear error messages: "Failed to render report template: {error}"
   - Fallback: Generate basic HTML without templates if rendering fails
   - Template syntax errors caught during development, not runtime (templates are embedded strings)

5. **Performance Considerations:**
   - CLI tools run once and exit - template compilation overhead is negligible
   - Jinja2 is optimized for repeated rendering; single renders are fast enough
   - No caching needed for one-time report generation
   - Embedded templates compile in-memory (no file I/O)
   - Typical render time: <10ms for reports with 1000s of data points

**Alternatives Considered:**

- **External template files:**
  - **Rejected:** Requires template file management, complicates distribution
  - Would need `package_data` in setup.py or bundling logic
  - Users might accidentally modify/delete templates

- **No templating (pure string formatting):**
  - **Rejected:** Current approach with f-strings is error-prone
  - Hard to maintain consistent HTML structure across tools
  - No escaping, security concerns with user data
  - Difficult to implement template inheritance

- **Alternative template engines (Mako, Chameleon):**
  - **Rejected:** Jinja2 is the de facto standard for Python
  - Better documentation, larger community
  - More familiar to Python developers
  - Excellent error messages

**Implementation Plan:**

```python
# utils/html_theme.py
THEME = {
    'colors': {
        'primary': '#007bff',
        'secondary': '#6c757d',
        'success': '#28a745',
        'warning': '#ffc107',
        'danger': '#dc3545',
        'info': '#17a2b8',
    },
    'gradients': {
        'purple': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'pink': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'blue': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'orange': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    },
    'chart_colors': [
        'rgba(255, 99, 132, 0.8)',
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)',
    ],
    'fonts': {
        'family': "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif",
        'monospace': "'Courier New', monospace",
    }
}

# Base template (embedded string in utils/html_templates.py)
BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Photo Admin Report{% endblock %}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        {{ shared_css }}
        {% block extra_css %}{% endblock %}
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    <script>
        {% block scripts %}{% endblock %}
    </script>
</body>
</html>"""

# Tool-specific template
PHOTO_STATS_TEMPLATE = """{% extends base_template %}
{% block title %}Photo Statistics Report{% endblock %}
{% block content %}
    <h1>📸 Photo Statistics Report</h1>
    <!-- Tool-specific content -->
{% endblock %}
"""

# Usage in photo_stats.py
from jinja2 import Template, TemplateError
from utils.html_templates import BASE_TEMPLATE, PHOTO_STATS_TEMPLATE
from utils.html_theme import THEME

def generate_html_report(self, output_path='photo_stats_report.html'):
    try:
        template = Template(PHOTO_STATS_TEMPLATE)
        html = template.render(
            base_template=BASE_TEMPLATE,
            theme=THEME,
            stats=self.stats,
            # ... other data
        )
        Path(output_path).write_text(html, encoding='utf-8')
    except TemplateError as e:
        print(f"Error rendering template: {e}")
        # Fallback to basic HTML generation
        self._generate_fallback_html(output_path)
```

**Dependencies:**
- Add `Jinja2>=3.1.0` to requirements.txt
- Minimal overhead: Jinja2 is ~100KB, no additional dependencies

---

## 2. Python Signal Handling (SIGINT/Ctrl+C)

### Decision: Standard Signal Handler with Graceful Cleanup

**Selected Approach:**
- Register SIGINT handler at program start using `signal.signal()`
- Implement global flag for graceful shutdown coordination
- Ensure cleanup of partial file writes using atomic write pattern
- Exit with code 130 (standard for SIGINT)
- Handle cross-platform differences with platform-specific logic

**Rationale:**

1. **Signal Handler Pattern:**
   - Use `signal.signal(signal.SIGINT, handler_func)` - Python's standard approach
   - Handler sets global flag and exits immediately for responsiveness
   - Current implementation in photo_pairing.py:37-43 is correct
   - Simple, readable, follows Python conventions

2. **Graceful Shutdown:**
   - Global `shutdown_requested` flag allows in-progress operations to finish
   - Cleanup happens in signal handler before exit
   - For photo-admin: minimal cleanup needed (no database, no network connections)
   - Primary concern: prevent partial cache file writes

3. **Preventing Partial File Writes:**
   - **Atomic write pattern:** Write to temporary file, then rename
   - `os.replace()` is atomic on POSIX systems (macOS, Linux)
   - On Windows: use `win32api.MoveFileEx()` with `MOVEFILE_REPLACE_EXISTING`
   - Delete temp file if interrupted before rename
   - Cache files: .photo_pairing_imagegroups.tmp → .photo_pairing_imagegroups
   - HTML reports: Less critical (users can re-run), but same pattern for consistency

4. **Cross-Platform Compatibility:**
   - SIGINT works on all platforms (POSIX, Windows)
   - Windows has limited signal support, but SIGINT/CTRL_C_EVENT work
   - Exit code 130: Standard on Unix/Linux/macOS, acceptable on Windows
   - Test on all target platforms (already covered by macOS in requirements)

5. **Integration with Long-Running Operations:**
   - Check `shutdown_requested` flag in loops (e.g., file scanning)
   - Break early and cleanup if interrupt detected
   - For photo-admin: scan_folder() could check flag every N files
   - User experience: Immediate feedback ("Interrupt received..."), then quick cleanup

**Alternatives Considered:**

- **No signal handling (default Python behavior):**
  - **Rejected:** Leaves garbage files, confusing error messages
  - Poor user experience
  - Current photo_pairing.py already implements signal handling (lines 37-43)

- **Context managers for cleanup:**
  - **Rejected as sole solution:** Context managers don't catch SIGINT
  - Still useful for normal cleanup (use both approaches)

- **atexit module:**
  - **Rejected:** Not called on SIGINT/SIGTERM by default
  - Would need signal handler to trigger normal exit
  - More complex than direct signal handling

- **Third-party libraries (e.g., signal-handler):**
  - **Rejected:** Overkill for simple CLI tools
  - Unnecessary dependency
  - Python's signal module is sufficient

**Implementation Plan:**

```python
# Improved signal handler with atomic file writes
import signal
import sys
import tempfile
from pathlib import Path

shutdown_requested = False
temp_files_to_cleanup = []

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested, temp_files_to_cleanup
    shutdown_requested = True

    print("\n\nInterrupt received (Ctrl+C)")
    print("Cleaning up...")

    # Remove any temporary files
    for temp_file in temp_files_to_cleanup:
        try:
            Path(temp_file).unlink(missing_ok=True)
        except Exception as e:
            print(f"Warning: Could not remove temp file {temp_file}: {e}")

    print("Exiting gracefully.")
    sys.exit(130)  # Standard exit code for SIGINT

def atomic_write(file_path, content):
    """Write file atomically to prevent partial writes on interrupt."""
    global temp_files_to_cleanup

    file_path = Path(file_path)
    # Create temp file in same directory (ensures same filesystem)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=file_path.parent,
        prefix=f".{file_path.name}.",
        suffix='.tmp'
    )
    temp_files_to_cleanup.append(temp_path)

    try:
        # Write content to temp file
        with open(temp_fd, 'w', encoding='utf-8') as f:
            f.write(content)

        # Atomic rename (POSIX) or move (Windows)
        if sys.platform == 'win32':
            # Windows: delete target first, then rename
            if file_path.exists():
                file_path.unlink()
            Path(temp_path).rename(file_path)
        else:
            # POSIX: atomic replace
            Path(temp_path).replace(file_path)

        temp_files_to_cleanup.remove(temp_path)
        return True

    except Exception as e:
        print(f"Error writing file {file_path}: {e}")
        Path(temp_path).unlink(missing_ok=True)
        temp_files_to_cleanup.remove(temp_path)
        return False

# Register handler at program start
signal.signal(signal.SIGINT, signal_handler)

# In scan_folder() - check for interrupts periodically
def scan_folder(folder_path, extensions):
    count = 0
    for file_path in folder_path.rglob('*'):
        if shutdown_requested:
            print("Scan interrupted by user")
            break

        # Process file...
        count += 1
        if count % 100 == 0:
            # Check interrupt every 100 files
            pass

    return results

# In save_cache() - use atomic write
def save_cache(folder_path, imagegroups, invalid_files, file_list_hash):
    cache_path = folder_path / '.photo_pairing_imagegroups'
    cache_data = {...}  # Build cache data
    content = json.dumps(cache_data, indent=2, default=str)

    return atomic_write(cache_path, content)
```

**Testing Strategy:**
- Manual testing: Press Ctrl+C at various points in execution
- Verify no partial files left behind
- Check exit code is 130
- Test on macOS (primary platform), Linux (CI), Windows (if applicable)

---

## 3. argparse Help Text Patterns

### Decision: RawDescriptionHelpFormatter with Structured Examples

**Selected Approach:**
- Use `argparse.RawDescriptionHelpFormatter` for formatted help text
- Include practical usage examples in `epilog` parameter
- Document configuration file locations in description
- Use consistent formatting across all tools
- Provide both simple and advanced usage examples

**Rationale:**

1. **Formatter Class Selection:**
   - **RawDescriptionHelpFormatter:** Preserves formatting in description/epilog
   - Allows multi-line examples with proper indentation
   - Essential for showing actual command-line examples
   - Current photo_pairing.py already uses this (line 800)

2. **Help Text Structure:**
   ```
   usage: tool [options] folder

   [Description - one paragraph]

   positional arguments:
     folder    Path to folder containing photos

   optional arguments:
     -h, --help  Show this help message
     --config    Path to configuration file

   Examples:
     [2-3 practical examples with explanations]

   Configuration:
     [Where tool looks for config files]

   [Footer with documentation link]
   ```

3. **Including Usage Examples:**
   - Place in `epilog` parameter (appears after argument descriptions)
   - Show common use cases first (80% use case)
   - Then advanced examples (optional arguments, edge cases)
   - Use realistic paths: `~/Photos/2025-01-Shoot`, not `/path/to/folder`
   - Include expected output or behavior in comments

4. **Documenting Required vs Optional Arguments:**
   - Use `required=True` for required arguments (argparse enforces)
   - Mark optional with `[optional]` in help text
   - Show defaults in help text: `default=%(default)s`
   - Use argument groups for related options:
     ```python
     config_group = parser.add_argument_group('Configuration')
     config_group.add_argument('--config', ...)
     ```

5. **Configuration File Documentation:**
   - Include config search order in tool description
   - Show how to specify custom config file
   - Reference detailed docs: "See docs/configuration.md for details"
   - Show example config snippet if relevant

**Alternatives Considered:**

- **ArgumentDefaultsHelpFormatter:**
  - **Rejected:** Doesn't preserve formatting for examples
  - Can combine with RawDescriptionHelpFormatter if needed:
    ```python
    class Formatter(argparse.RawDescriptionHelpFormatter,
                   argparse.ArgumentDefaultsHelpFormatter):
        pass
    ```

- **Plain text help (no argparse):**
  - **Rejected:** Reinventing the wheel
  - argparse provides consistent parsing, validation, and --help generation
  - Users expect --help to work

- **Man pages:**
  - **Rejected for now:** Overkill for simple CLI tools
  - Requires separate documentation infrastructure
  - Can add later if needed (using help2man)

- **Rich/click for fancy help:**
  - **Rejected:** Adds heavy dependencies
  - argparse is stdlib, always available
  - Current tools use argparse (photo_pairing.py)
  - Consistency more important than fancy colors

**Implementation Plan:**

```python
# Standardized argparse pattern for photo-admin tools
import argparse
import sys

def create_argument_parser():
    """Create and configure argument parser with standardized help."""

    # Tool-specific description (1-2 sentences)
    description = """
Analyze photo collections for orphaned files and sidecar issues.
Generates an interactive HTML report with statistics and visualizations.
    """.strip()

    # Epilog with examples and config info
    epilog = """
Examples:
  # Analyze a photo folder (uses default config)
  %(prog)s ~/Photos/2025-01-Shoot

  # Specify output location and custom config
  %(prog)s ~/Photos/2025-01-Shoot -o report.html -c custom-config.yaml

  # Analyze remote/mounted volume
  %(prog)s /Volumes/PhotoDrive/RAW

Configuration Files (checked in order):
  1. ./config/config.yaml          (current directory)
  2. ./config.yaml                 (current directory)
  3. ~/.photo_stats_config.yaml   (home directory)
  4. <script-dir>/config/config.yaml (installation directory)

  To create a config file, copy config/template-config.yaml
  See docs/configuration.md for full documentation

Documentation:
  Installation:   docs/installation.md
  Configuration:  docs/configuration.md
  Tool guide:     docs/photostats.md
    """.strip()

    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Positional arguments
    parser.add_argument(
        'folder',
        type=str,
        help='path to folder containing photos to analyze'
    )

    # Optional arguments with argument group
    output_group = parser.add_argument_group('Output options')
    output_group.add_argument(
        '-o', '--output',
        type=str,
        default='photo_stats_report.html',
        metavar='FILE',
        help='output HTML report path (default: %(default)s)'
    )

    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        '-c', '--config',
        type=str,
        metavar='FILE',
        help='path to configuration file (default: auto-detect)'
    )

    return parser

def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate arguments
    folder_path = Path(args.folder).resolve()
    if not folder_path.exists():
        parser.error(f"Folder not found: {folder_path}")

    if not folder_path.is_dir():
        parser.error(f"Not a directory: {folder_path}")

    # ... rest of main logic
```

**Comparison with Current Implementation:**

Current photo_stats.py (lines 601-611):
- ❌ Uses plain print() instead of argparse
- ❌ Manual usage message formatting
- ❌ No validation or error handling
- ✅ Does show config file locations
- ✅ Includes examples

Current photo_pairing.py (lines 798-820):
- ✅ Uses argparse with RawDescriptionHelpFormatter
- ✅ Includes practical examples
- ✅ Shows workflow steps
- ❌ Missing config file documentation
- ❌ No optional arguments (could add --output, --config)

**Migration Plan:**
1. Update photo_stats.py to use argparse (currently uses manual parsing)
2. Standardize both tools with consistent help format
3. Add common optional arguments: --output, --config, --quiet/--verbose
4. Test help text readability: `./tool --help | less`

---

## Summary of Decisions

| Topic | Decision | Key Benefits |
|-------|----------|--------------|
| **Templates** | Jinja2 with embedded templates + inheritance | Consistency, maintainability, security |
| **Theme** | Shared constants in utils/html_theme.py | Single source of truth for styling |
| **Signal Handling** | Standard signal handler + atomic writes | Graceful shutdown, no partial files |
| **Interrupts** | Global flag + periodic checks in loops | Responsive, clean exit |
| **Exit Codes** | 130 for SIGINT, 0 for success, 1 for errors | Standard Unix conventions |
| **Help Text** | argparse with RawDescriptionHelpFormatter | Consistent, well-formatted help |
| **Examples** | Practical examples in epilog | Users can copy-paste commands |
| **Config Docs** | Include search order in help text | Self-documenting tools |

---

## Dependencies to Add

```txt
# requirements.txt additions
Jinja2>=3.1.0       # Template engine for HTML reports
```

No additional dependencies needed for signal handling or argparse (stdlib).

---

## Implementation Priority

1. **High Priority:**
   - Create utils/html_theme.py with shared constants
   - Create utils/html_templates.py with base template
   - Update photo_stats.py to use argparse (currently manual parsing)
   - Implement atomic write pattern in both tools

2. **Medium Priority:**
   - Migrate both tools to Jinja2 templates
   - Standardize help text format
   - Add common CLI options (--output, --config, --quiet)

3. **Low Priority:**
   - Add progress indicators that respect shutdown flag
   - Create template testing suite
   - Consider adding --version flag

---

## Testing Checklist

- [ ] Template rendering with valid data
- [ ] Template rendering with edge cases (empty data, None values)
- [ ] Template error handling (malformed data)
- [ ] Signal handling: Ctrl+C during file scan
- [ ] Signal handling: Ctrl+C during file write
- [ ] Signal handling: Verify no partial files left
- [ ] Signal handling: Check exit code is 130
- [ ] Help text: Verify formatting with `--help`
- [ ] Help text: Test on narrow terminal (80 columns)
- [ ] Cross-platform: Test on macOS (primary platform)
- [ ] Configuration: Verify all search paths work

---

## References

### Jinja2 Documentation
- Official docs: https://jinja.palletsprojects.com/
- Template Designer Documentation: https://jinja.palletsprojects.com/en/3.1.x/templates/
- API Documentation: https://jinja.palletsprojects.com/en/3.1.x/api/

### Python Signal Handling
- Official docs: https://docs.python.org/3/library/signal.html
- PEP 475 - Retry system calls failing with EINTR: https://www.python.org/dev/peps/pep-0475/
- Atomic file writes: https://docs.python.org/3/library/os.html#os.replace

### argparse Best Practices
- Official docs: https://docs.python.org/3/library/argparse.html
- PEP 389 - argparse - New Command Line Parsing Module: https://www.python.org/dev/peps/pep-0389/
- Click documentation (for comparison): https://click.palletsprojects.com/

### Exit Codes
- Bash Exit Codes: https://tldp.org/LDP/abs/html/exitcodes.html
- POSIX standard: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_08_02

---

**Document Status:** Complete
**Next Steps:** Implement changes according to priority order above
**Review Date:** 2025-12-25
