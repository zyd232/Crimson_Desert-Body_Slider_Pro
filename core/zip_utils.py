"""
zip_utils: ZIP file utilities with Zstd (Method 93) support.

Handles:
- Extraction of ZIP entries using standard methods and Zstd-decompressed
  entries (compress_type == 93, as defined in ITU-T T.844 / RFC 8878).
- Creation of Zstd-compressed ZIP archives for export.

Recommended library: zstd (pip install zstd)
Fallback: falls back to ZIP_DEFLATED when the library is unavailable.

Design note
-----------
Python's built-in ``zipfile`` module raises
``ZipImportError: That compression method is not supported`` when it
encounters a Zstd-compressed entry (method 93) on Python < 3.14, and even
on >= 3.14 it may fail silently if the underlying ``zstd`` bindings are
missing.  To work reliably across all Python versions we **never call**
``zf.open()`` or ``zf.read()`` for method-93 entries.  Instead we read the
raw compressed bytes directly from the ZIP file at the correct file-offset
and decompress them with the ``zstd`` package.
"""

import os
import struct
import zipfile
from typing import Optional


# ---------------------------------------------------------------------------
# Lazy-import zstd so the application still starts when it is absent
# ---------------------------------------------------------------------------
_zstd_module = None

def _get_zstd():
    """Return the zstd module, or raise ImportError with a helpful message."""
    global _zstd_module
    if _zstd_module is not None:
        return _zstd_module
    try:
        import zstd
        _zstd_module = zstd
        return zstd
    except ImportError:
        raise ImportError(
            "zstd library is required to extract ZIP files with Zstd compression "
            "(Method 93). Install it with:  pip install zstd"
        )

def has_zstd() -> bool:
    """Check if zstd library is available."""
    global _zstd_module
    if _zstd_module is not None:
        return True
    try:
        import zstd
        _zstd_module = zstd
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Internal: read raw compressed data from a ZIP file
# ---------------------------------------------------------------------------

def _read_raw_compressed(zip_path: str, info: zipfile.ZipInfo) -> bytes:
    """Read the *raw compressed* bytes for a ZIP entry without decompressing.

    This bypasses Python's ``zipfile`` module entirely (which does not support
    method 93 on all Python versions), so we can feed the data to our own
    Zstd decompressor.

    Uses ZipInfo's compress_size (from central directory) which is always
    correct, even for ZIP64 archives.
    """
    header_offset = info.header_offset

    with open(zip_path, "rb") as f:
        f.seek(header_offset)

        # -- Local file header (minimum 30 bytes) --
        header = f.read(30)
        (sig, _, _, _, _, _, _, _, _,
         name_len, extra_len) = struct.unpack('<IHHHHHIIIHH', header)

        # Validate signature
        if sig != 0x04034B50:
            raise zipfile.BadZipFile(
                f"Invalid local file header for '{info.filename}'"
            )

        # Use ZipInfo's compress_size (from central directory) which handles
        # ZIP64 correctly. ZipInfo.file_size = uncompressed size.
        compress_size = info.compress_size

        # Skip filename and extra field to reach compressed data
        data_offset = header_offset + 30 + name_len + extra_len
        f.seek(data_offset)
        raw_data = f.read(compress_size)

        return raw_data


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _decompress_zstd_entry(zip_path: str, info: zipfile.ZipInfo) -> bytes:
    """Decompress a Zstd-compressed (method 93) ZIP entry.

    Reads raw compressed bytes from the ZIP file and decompresses with the
    ``zstd`` package.
    """
    zstd = _get_zstd()
    raw_compressed = _read_raw_compressed(zip_path, info)
    return zstd.decompress(raw_compressed)


def decompress_entry(zip_path: Optional[str], entry: zipfile.ZipInfo,
                     stream=None) -> bytes:
    """Decompress a single ZIP entry, handling Zstd (method 93) automatically.

    Parameters
    ----------
    zip_path : str or None
        Path to the ZIP file on disk.  Required when *entry* uses Zstd
        compression (method 93).
    entry : zipfile.ZipInfo
        Metadata for the ZIP entry.
    stream : BinaryIO, optional
        Already-opened stream from ``zf.open(info)``.  Used only for
        non-Zstd entries.

    Returns
    -------
    bytes
        The fully decompressed data.

    Raises
    ------
    ImportError
        When the entry uses Zstd compression but the *zstd* package is not
        installed.
    """
    if entry.compress_type == 93:
        # Zstd-compressed entry – read raw bytes and decompress manually
        # because Python's zipfile may not support method 93.
        if zip_path is None:
            raise RuntimeError(
                "zip_path is required for Zstd-compressed entries"
            )
        return _decompress_zstd_entry(zip_path, entry)
    else:
        # Standard method (stored / deflate / etc.) – use zipfile normally
        if stream is not None:
            return stream.read()
        # Fallback: should not happen in normal usage
        raise RuntimeError(
            "stream is required for non-Zstd entries"
        )


def extract_zip(zip_path: str, target_dir: str, long_path_callback=None):
    """Extract an entire ZIP archive to *target_dir*, supporting Zstd entries.

    Parameters
    ----------
    zip_path : str
        Path to the ``.zip`` file.
    target_dir : str
        Destination directory (will be created if it does not exist).
    long_path_callback : callable, optional
        If provided, every path (directory and file) is passed through this
        callback *before* use.  This allows Windows long-path prefixes
        (``\\\\?\\...``) to be applied.  The callback should accept a single
        ``str`` and return a ``str``.

    Raises
    ------
    zipfile.BadZipFile
        When the file is not a valid ZIP archive.
    ImportError
        When a Zstd-compressed entry is encountered but the *zstd* package
        is not available.
    """
    if long_path_callback is None:
        long_path_callback = lambda p: p

    os.makedirs(target_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            target = os.path.join(target_dir, info.filename)
            target = long_path_callback(target)

            # Directory entry
            if info.filename.endswith("/"):
                os.makedirs(target, exist_ok=True)
                continue

            # Ensure parent directory exists
            dir_path = os.path.dirname(target)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            # Decompress and write
            if info.compress_type == 93:
                # Zstd: read raw + decompress manually (bypass zipfile)
                data = _decompress_zstd_entry(zip_path, info)
            else:
                # Standard: use zipfile.open() safely
                with zf.open(info) as src:
                    data = src.read()

            with open(target, "wb") as dst:
                dst.write(data)


def read_zip_string(zip_path: str, zip_handle: zipfile.ZipFile, name: str) -> bytes:
    """Read a file inside a ZIP as bytes, with Zstd support.

    Parameters
    ----------
    zip_path : str
        Path to the ZIP file on disk (required for Zstd entries).
    zip_handle : zipfile.ZipFile
        An already opened ZipFile (mode ``'r'``).
    name : str
        Archive member name.

    Returns
    -------
    bytes
    """
    info = zip_handle.getinfo(name)

    if info.compress_type == 93:
        # Zstd: read raw + decompress manually
        return _decompress_zstd_entry(zip_path, info)
    else:
        # Standard: use zipfile normally
        with zip_handle.open(info) as stream:
            return stream.read()


# ---------------------------------------------------------------------------
# Single-file Zstd compression (for temp-based ZIP packaging)
# ---------------------------------------------------------------------------

def compress_to_zst(src_path: str, dst_path: str, compress_level: int = 3) -> str:
    """Compress a single file with Zstd and write to dst_path.

    Parameters
    ----------
    src_path : str
        Path to the source file.
    dst_path : str
        Path for the output ``.zst`` file.
    compress_level : int
        Zstd compression level (1-22, default 3).

    Returns
    -------
    str
        The destination path on success.
    """
    zstd = _get_zstd()
    with open(src_path, "rb") as f:
        data = f.read()
    compressed = zstd.compress(data, compress_level)
    with open(dst_path, "wb") as f:
        f.write(compressed)
    return dst_path


def decompress_zst_file(src_path: str, dst_path: str) -> str:
    """Decompress a single .zst file.

    Parameters
    ----------
    src_path : str
        Path to the ``.zst`` file.
    dst_path : str
        Path for the decompressed output file.

    Returns
    -------
    str
        The destination path on success.
    """
    zstd = _get_zstd()
    with open(src_path, "rb") as f:
        compressed = f.read()
    data = zstd.decompress(compressed)
    with open(dst_path, "wb") as f:
        f.write(data)
    return dst_path


# ---------------------------------------------------------------------------
# Zstd ZIP creation — pure binary (no zipfile module for writing)
# ---------------------------------------------------------------------------
# Python's zipfile.writestr() raises "That compression method is not supported"
# for compress_type=93 on Python < 3.14.  Even writing as STORED then patching
# is unreliable because zipfile may re-compress the data.
#
# Solution: write the entire ZIP file manually (local headers + central dir + EOCD).

import time as _time
import zlib as _zlib


def _zip_mod_date(year: int, month: int, day: int) -> int:
    """Encode date for ZIP: ((year-1980)<<9) | (month<<5) | day."""
    return ((year - 1980) << 9) | (month << 5) | day


def _zip_mod_time(hour: int, minute: int, second: int) -> int:
    """Encode time for ZIP: (hour<<11) | (minute<<5) | (second//2)."""
    return (hour << 11) | (minute << 5) | (second // 2)


def _write_local_header(f, filename: bytes, comp_data: bytes, uncomp_data: bytes,
                        comp_type: int, mtime: tuple):
    """Write a local file header (30 bytes) + filename + data.

    mtime: (year, month, day, hour, minute, second) from time.localtime()[:6]
    """
    if len(mtime) >= 6:
        mod_date = _zip_mod_date(mtime[0], mtime[1], mtime[2])
        mod_time = _zip_mod_time(mtime[3], mtime[4], mtime[5])
    else:
        mod_date, mod_time = 0, 0

    crc = _zlib.crc32(uncomp_data) & 0xFFFFFFFF
    # Local file header: 30 bytes
    # I(sig) + H(version) + H(flags) + H(comp_method) + H(mod_time) + H(mod_date)
    # + I(crc32) + I(comp_size) + I(uncomp_size) + H(name_len) + H(extra_len)
    f.write(struct.pack('<IHHHHHIIIHH',
        0x04034B50,  # signature
        20,          # version needed (2.0)
        0,           # flags
        comp_type,   # compression method
        mod_time,    # last mod time
        mod_date,    # last mod date
        crc,         # crc-32
        len(comp_data),   # compressed size
        len(uncomp_data), # uncompressed size
        len(filename),    # filename length
        0,           # extra field length
    ))
    f.write(filename)
    f.write(comp_data)


def _write_cd_entry(f, filename: bytes, comp_data: bytes, uncomp_data: bytes,
                    comp_type: int, mtime: tuple, header_offset: int):
    """Write a central directory record (46 bytes fixed + filename + extra + comment).

    mtime: (year, month, day, hour, minute, second) from time.localtime()[:6]
    """
    if len(mtime) >= 6:
        mod_date = _zip_mod_date(mtime[0], mtime[1], mtime[2])
        mod_time = _zip_mod_time(mtime[3], mtime[4], mtime[5])
    else:
        mod_date, mod_time = 0, 0

    crc = _zlib.crc32(uncomp_data) & 0xFFFFFFFF
    # Central directory record: 46 bytes fixed
    # I(sig) + H(ver_made) + H(ver_need) + H(flags) + H(comp_method)
    # + H(mod_time) + H(mod_date) + I(crc32) + I(comp_size) + I(uncomp_size)
    # + H(name_len) + H(extra_len) + H(comment_len) + H(disk_num)
    # + H(internal_attr) + I(external_attr) + I(header_offset)
    f.write(struct.pack('<IHHHHHHIIIHHHHHII',
        0x02014B50,  # signature
        45,          # version made by (4.5)
        20,          # version needed (2.0)
        0,           # flags
        comp_type,   # compression method
        mod_time,    # last mod time
        mod_date,    # last mod date
        crc,         # crc-32
        len(comp_data),   # compressed size
        len(uncomp_data), # uncompressed size
        len(filename),    # filename length
        0,           # extra field length
        0,           # file comment length
        0,           # disk number start
        0,           # internal file attributes
        0,           # external file attributes
        header_offset,   # relative offset of local header
    ))
    f.write(filename)


def create_zstd_zip(
    output_path: str,
    file_list: list,
    progress_callback=None,
    compress_level: int = 3,
) -> str:
    """Create a Zstd-compressed ZIP archive (Method 93) by writing raw bytes.

    Bypasses Python's zipfile module entirely to avoid
    "That compression method is not supported" on Python < 3.14.
    """
    zstd = _get_zstd()
    total = len(file_list)

    cd_entries = []  # list of (cd_bytes, filename_bytes, header_offset)
    uncomp_sizes = []

    with open(output_path, "wb") as f:
        for idx, (src_path, arcname) in enumerate(file_list, 1):
            with open(src_path, "rb") as sf:
                uncomp_data = sf.read()

            comp_data = zstd.compress(uncomp_data, compress_level)

            file_stat = os.stat(src_path)
            mtime = _time.localtime(file_stat.st_mtime)[:6]
            filename_bytes = arcname.encode('utf-8')

            header_offset = f.tell()
            _write_local_header(f, filename_bytes, comp_data, uncomp_data, 93, mtime)

            # Store info for central directory
            cd_offset_data = (filename_bytes, comp_data, uncomp_data, mtime, header_offset)
            cd_entries.append(cd_offset_data)

            if progress_callback is not None:
                progress_callback(idx, total, arcname)

        # Write central directory
        cd_start = f.tell()
        cd_size = 0
        for filename_bytes, comp_data, uncomp_data, mtime, header_offset in cd_entries:
            before = f.tell()
            _write_cd_entry(f, filename_bytes, comp_data, uncomp_data, 93, mtime, header_offset)
            cd_size += f.tell() - before

        # Write EOCD
        f.write(struct.pack('<IHHHHIIH',
            0x06054B50,  # signature
            0,           # number of this disk
            0,           # disk where CD starts
            len(cd_entries),  # number of CD records on this disk
            len(cd_entries),  # total number of CD records
            cd_size,     # size of central directory
            cd_start,    # offset of start of central directory
            0,           # .zip file comment length
        ))

    return output_path


def create_zip(
    output_path: str,
    file_list: list,
    progress_callback=None,
    use_zstd: bool = True,
    zstd_level: int = 3,
) -> str:
    """Create a ZIP archive, preferring Zstd compression when available.

    Parameters
    ----------
    output_path : str
        Path for the output ``.zip`` file.
    file_list : list of tuple
        Each element is ``(src_path, arcname)``.
    progress_callback : callable, optional
        Called as ``callback(current, total, message)``.
    use_zstd : bool
        If True and zstd is available, use Zstd (Method 93).
        Otherwise fall back to ZIP_DEFLATED.
    zstd_level : int
        Zstd compression level when Zstd is used.

    Returns
    -------
    str
        The output path on success.
    """
    if use_zstd and has_zstd():
        return create_zstd_zip(
            output_path, file_list,
            progress_callback=progress_callback,
            compress_level=zstd_level,
        )
    else:
        # Fallback: standard DEFLATED
        total = len(file_list)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, (src_path, arcname) in enumerate(file_list, 1):
                zf.write(src_path, arcname)
                if progress_callback is not None:
                    progress_callback(idx, total, arcname)
        return output_path
