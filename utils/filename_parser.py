#!/usr/bin/env python3
"""
Filename Parser for Photo Administration Tools

This module provides filename validation and parsing for photo files following
the naming convention: {CAMERA_ID}{COUNTER}[-{PROPERTY}]*{.extension}

Example valid filenames:
- AB3D0001.dng
- XYZW0035-HDR.tiff
- AB3D0042-2-HDR_BW.cr3

Copyright (C) 2024 Fabrice Guiot

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import re


class FilenameParser:
    """
    Validates and parses photo filenames following a specific naming convention.

    Filename format: {CAMERA_ID}{COUNTER}[-{PROPERTY}]*{.extension}
    - CAMERA_ID: 4 uppercase alphanumeric characters [A-Z0-9]{4}
    - COUNTER: 4 digits from 0001 to 9999 (0000 not allowed)
    - PROPERTY: Optional dash-prefixed alphanumeric + spaces + underscores
    - Extension: Case-insensitive file extension
    """

    # Filename validation pattern
    # Format: 4 uppercase alphanumeric + 4 digits (0001-9999) + optional properties + extension
    # Properties can contain letters, digits, spaces, and underscores
    # Extensions are case-insensitive (both .DNG and .dng are valid)
    VALID_FILENAME_PATTERN = re.compile(
        r'^[A-Z0-9]{4}(0[0-9]{3}|[1-9][0-9]{3})(-[A-Za-z0-9 _]+)*\.[a-zA-Z0-9]+$'
    )

    @staticmethod
    def validate_filename(filename):
        """
        Validate if filename matches the expected pattern.

        Args:
            filename: The filename to validate (without path)

        Returns:
            tuple: (is_valid, error_reason)
                is_valid: Boolean indicating if filename is valid
                error_reason: String with specific error reason if invalid, None if valid
        """
        # Check basic pattern
        if not FilenameParser.VALID_FILENAME_PATTERN.match(filename):
            # Determine specific reason
            name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

            # Check camera ID (first 4 characters)
            if len(name_without_ext) < 4:
                return False, "Filename too short - camera ID must be 4 characters"

            camera_id = name_without_ext[:4]
            if not re.match(r'^[A-Z0-9]{4}$', camera_id):
                if camera_id.islower() or any(c.islower() for c in camera_id):
                    return False, "Camera ID must be uppercase alphanumeric [A-Z0-9]"
                else:
                    return False, "Camera ID must be exactly 4 uppercase alphanumeric characters"

            # Check counter (characters 5-8)
            if len(name_without_ext) < 8:
                return False, "Counter must be 4 digits"

            counter = name_without_ext[4:8]
            if not re.match(r'^(0[0-9]{3}|[1-9][0-9]{3})$', counter):
                if counter == '0000':
                    return False, "Counter cannot be 0000 - must be 0001-9999"
                elif not counter.isdigit():
                    return False, "Counter must be 4 digits"
                else:
                    return False, "Counter must be 4 digits between 0001 and 9999"

            # Check for empty properties (double dash or trailing dash)
            if '--' in name_without_ext or name_without_ext.endswith('-'):
                return False, "Empty property name detected"

            # Check for invalid characters in properties
            if len(name_without_ext) > 8:
                properties_part = name_without_ext[8:]
                if not re.match(r'^(-[A-Za-z0-9 _]+)*$', properties_part):
                    return False, "Invalid characters in property name"

        return True, None

    @staticmethod
    def parse_filename(filename):
        """
        Parse a valid filename into its components.

        Args:
            filename: The filename to parse (without path)

        Returns:
            dict: {
                'camera_id': str,      # First 4 characters
                'counter': str,        # Characters 5-8
                'properties': list,    # List of dash-prefixed properties (without dashes)
                'extension': str       # File extension (with dot)
            }
            Returns None if filename is invalid
        """
        is_valid, _ = FilenameParser.validate_filename(filename)
        if not is_valid:
            return None

        # Split filename and extension
        name_without_ext, extension = filename.rsplit('.', 1)
        extension = '.' + extension

        # Extract camera ID and counter
        camera_id = name_without_ext[:4]
        counter = name_without_ext[4:8]

        # Extract properties (everything after position 8)
        properties = []
        if len(name_without_ext) > 8:
            properties_part = name_without_ext[8:]
            # Split by dash and filter out empty strings
            properties = [p for p in properties_part.split('-') if p]

        return {
            'camera_id': camera_id,
            'counter': counter,
            'properties': properties,
            'extension': extension
        }

    @staticmethod
    def detect_property_type(property_str):
        """
        Detect if a property is a separate image identifier or processing method.

        Args:
            property_str: The property string (without leading dash)

        Returns:
            str: 'separate_image' if all-numeric, 'processing_method' otherwise
        """
        return 'separate_image' if property_str.isdigit() else 'processing_method'
