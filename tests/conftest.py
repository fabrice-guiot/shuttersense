"""
Pytest configuration and fixtures for photo_stats tests
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_photo_dir(tmp_path):
    """Create a temporary directory with sample photo files."""
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()

    # Create subdirectories
    subdir1 = photo_dir / "2024-01"
    subdir1.mkdir()
    subdir2 = photo_dir / "2024-02"
    subdir2.mkdir()

    # Create fake photo files (empty files with correct extensions)
    files = [
        photo_dir / "IMG_001.dng",
        photo_dir / "IMG_001.xmp",
        photo_dir / "IMG_002.cr3",
        photo_dir / "IMG_002.xmp",
        photo_dir / "IMG_003.tiff",
        photo_dir / "IMG_003.xmp",
        subdir1 / "IMG_100.dng",
        subdir1 / "IMG_100.xmp",
        subdir1 / "IMG_101.cr3",  # Orphaned - no XMP
        subdir2 / "IMG_200.tif",
        subdir2 / "IMG_200.xmp",
        subdir2 / "IMG_201.xmp",  # Orphaned - no image
    ]

    for file_path in files:
        file_path.write_bytes(b"fake photo data" * 100)  # ~1.5KB per file

    return photo_dir


@pytest.fixture
def sample_xmp_content():
    """Sample XMP file content with common metadata."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 6.0.0">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:xmp="http://ns.adobe.com/xap/1.0/"
        xmlns:tiff="http://ns.adobe.com/tiff/1.0/"
        xmlns:exif="http://ns.adobe.com/exif/1.0/"
        xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
      <dc:format>image/dng</dc:format>
      <dc:creator>
        <rdf:Seq>
          <rdf:li>Test Photographer</rdf:li>
        </rdf:Seq>
      </dc:creator>
      <xmp:CreatorTool>Adobe Lightroom 12.0</xmp:CreatorTool>
      <xmp:CreateDate>2024-01-15T10:30:00</xmp:CreateDate>
      <xmp:Rating>5</xmp:Rating>
      <tiff:Make>Canon</tiff:Make>
      <tiff:Model>Canon EOS R5</tiff:Model>
      <exif:ISO>400</exif:ISO>
      <exif:FocalLength>85</exif:FocalLength>
      <photoshop:DateCreated>2024-01-15</photoshop:DateCreated>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''


@pytest.fixture
def temp_xmp_file(tmp_path, sample_xmp_content):
    """Create a temporary XMP file with sample metadata."""
    xmp_file = tmp_path / "test.xmp"
    xmp_file.write_text(sample_xmp_content)
    return xmp_file


@pytest.fixture
def empty_dir(tmp_path):
    """Create an empty temporary directory."""
    empty = tmp_path / "empty"
    empty.mkdir()
    return empty


@pytest.fixture
def mixed_file_dir(tmp_path):
    """Create a directory with both photo and non-photo files."""
    mixed_dir = tmp_path / "mixed"
    mixed_dir.mkdir()

    # Photo files
    (mixed_dir / "photo1.dng").write_bytes(b"data" * 100)
    (mixed_dir / "photo1.xmp").write_bytes(b"data" * 50)

    # Non-photo files (should be ignored)
    (mixed_dir / "readme.txt").write_text("readme")
    (mixed_dir / "script.py").write_text("print('hello')")
    (mixed_dir / "image.jpg").write_bytes(b"jpeg")

    return mixed_dir
