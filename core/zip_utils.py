"""
zip_utils: ZIP file utilities with Zstd (Method 93) support.

Handles:
- Extraction of ZIP entries using standard methods and Zstd-decompressed
  entries (compress_type == 93, as defined in ITU-T T.844 / RFC 8878).
- Creation of Zstd-compressed (Method 93) ZIP archives with **ZIP64 support**
  and **streaming compression** so archives and individual files exceeding
  4 GiB can be produced without holding all data in memory.

Recommended library: zstandard (pip install zstandard)
Fallback: falls back to ZIP_DEFLATED when the library is unavailable.

Design note
-----------
Python's built-in ``zipfile`` module raises
``NotImplementedError: That compression method is not supported`` when it
encounters a Zstd-compressed entry (method 93) on Python < 3.14, and even
on >= 3.14 it may fail silently if the underlying ``zstandard`` bindings are
missing.  To work reliably across all Python versions we **never call**
``zf.open()`` or ``zf.read()`` for method-93 entries.  Instead we read the
raw compressed bytes directly from the ZIP file at the correct file-offset
and decompress them with the ``zstandard`` package.

Streaming write
---------------
``create_zstd_zip`` writes each entry's local-file-header first as a
placeholder, then streams the source file through a zstd ``compressobj``
in fixed-size chunks (writing each compressed chunk to disk immediately and
accumulating the CRC32 of the *uncompressed* data), then seeks back to
patch the real sizes/CRC into the header.  Peak memory is therefore a
single chunk buffer (~1 MiB), independent of file or archive size.
"""

import os
import struct
import zipfile
from typing import Optional


# ---------------------------------------------------------------------------
# Lazy-import zstandard so the application still starts when it is absent
# ---------------------------------------------------------------------------
_zstd_module = None

def _get_zstd():
    """Return the zstandard module, or raise ImportError with a helpful message."""
    global _zstd_module
    if _zstd_module is not None:
        return _zstd_module
    try:
        import zstandard
        _zstd_module = zstandard
        return zstandard
    except ImportError:
        raise ImportError(
            "zstandard library is required to extract ZIP files with Zstd "
            "compression (Method 93). Install it with:  pip install zstandard"
        )

def has_zstd() -> bool:
    """Check if the zstandard library is available."""
    global _zstd_module
    if _zstd_module is not None:
        return True
    try:
        import zstandard
        _zstd_module = zstandard
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
    ``zstandard`` package.

    Uses ``max_output_size`` so that frames without an embedded content size
    (e.g. those produced by streaming compressors) can still be decoded in a
    single call; the value is derived from the ZIP central directory's
    ``file_size`` (which is correct even for ZIP64 archives).
    """
    zstandard = _get_zstd()
    raw_compressed = _read_raw_compressed(zip_path, info)
    dctx = zstandard.ZstdDecompressor()
    # file_size is the uncompressed size from the central directory. Give a
    # generous headroom in case of slightly off metadata; for streaming
    # frames without content size this bound is required by zstandard.
    expected = info.file_size if info.file_size and info.file_size > 0 else len(raw_compressed) * 8
    try:
        return dctx.decompress(raw_compressed, max_output_size=expected + 1024)
    except zstandard.ZstdError:
        # Fallback: stream-decompress without a size bound.
        with dctx.stream_reader(__import__("io").BytesIO(raw_compressed)) as reader:
            return reader.read()


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


def _build_zip64_lfh_extra(uncomp_size: int, comp_size: int) -> bytes:
    """Build ZIP64 extra field (tag 0x0001) for a *local file header*.

    Per APPNOTE 4.5.3 the ZIP64 extended information field in the local
    header may contain, in this fixed order, only the fields that
    overflow 32 bits:

        1. Original Uncompressed Size  (uint64, optional)
        2. Compressed Size              (uint64, optional)

    The relative offset of the local header and disk start number are
    *not* permitted here (they belong to central-directory entries only).
    """
    payload = bytearray()
    if uncomp_size >= 0xFFFFFFFF:
        payload.extend(struct.pack('<Q', uncomp_size))
    if comp_size >= 0xFFFFFFFF:
        payload.extend(struct.pack('<Q', comp_size))
    if not payload:
        return b''
    return struct.pack('<HH', 0x0001, len(payload)) + bytes(payload)


def _build_zip64_cd_extra(uncomp_size: int, comp_size: int,
                          header_offset: int) -> bytes:
    """Build ZIP64 extra field (tag 0x0001) for a *central directory entry*.

    Per APPNOTE 4.5.3 the ZIP64 extended information field in a central
    directory record may contain, in this fixed order, only the fields
    that overflow 32 bits:

        1. Original Uncompressed Size  (uint64, optional)
        2. Compressed Size             (uint64, optional)
        3. Relative Offset of Local Header (uint64, optional)
        4. Disk Start Number           (uint32, optional; always 0 here)

    Disk start number never overflows for single-disk archives, so it is
    omitted.
    """
    payload = bytearray()
    if uncomp_size >= 0xFFFFFFFF:
        payload.extend(struct.pack('<Q', uncomp_size))
    if comp_size >= 0xFFFFFFFF:
        payload.extend(struct.pack('<Q', comp_size))
    if header_offset >= 0xFFFFFFFF:
        payload.extend(struct.pack('<Q', header_offset))
    if not payload:
        return b''
    return struct.pack('<HH', 0x0001, len(payload)) + bytes(payload)


# Size of the streaming read/compress chunk (1 MiB). Keeps peak memory at a
# single chunk buffer regardless of file or archive size.
_ZIP_STREAM_CHUNK = 1 << 20

# Offsets (from start of the fixed 30-byte local file header) of the fields
# the streaming writer patches after the compressed payload is known:
#   sig(4) ver(2) flags(2) method(2) time(2) date(2) crc(4) csize(4) usize(4)
#      0      4       6        8       10     12     14     18      22
_LFH_CRC_OFFSET = 14
_LFH_CSIZE_OFFSET = 18
_LFH_USIZE_OFFSET = 22


def _write_local_header(f, filename: bytes, crc: int, comp_size: int,
                        uncomp_size: int, comp_type: int, mtime: tuple,
                        need_zip64: bool = False):
    """Write a local file header (30 bytes) + filename + extra field.

    The compressed payload itself is **not** written here; the caller writes
    it to *f* immediately afterwards.  This signature takes already-computed
    ``crc`` / ``comp_size`` / ``uncomp_size`` so it works for both the buffered
    and the streaming code paths.

    need_zip64: when True, overflow 32-bit fields are stored as the
        0xFFFFFFFF sentinel and a ZIP64 extra field (tag 0x0001) is
        appended carrying the real 64-bit sizes. Otherwise everything
        is written with plain 32-bit fields.
    """
    if len(mtime) >= 6:
        mod_date = _zip_mod_date(mtime[0], mtime[1], mtime[2])
        mod_time = _zip_mod_time(mtime[3], mtime[4], mtime[5])
    else:
        mod_date, mod_time = 0, 0

    if need_zip64:
        comp_field = 0xFFFFFFFF if comp_size >= 0xFFFFFFFF else comp_size
        uncomp_field = 0xFFFFFFFF if uncomp_size >= 0xFFFFFFFF else uncomp_size
        extra = _build_zip64_lfh_extra(uncomp_size, comp_size)
        version_needed = 45  # 4.5 required for ZIP64
    else:
        comp_field = comp_size
        uncomp_field = uncomp_size
        extra = b''
        version_needed = 20  # 2.0

    # Local file header: 30 bytes fixed
    f.write(struct.pack('<IHHHHHIIIHH',
        0x04034B50,          # signature
        version_needed,      # version needed
        0,                   # flags
        comp_type,           # compression method
        mod_time,            # last mod time
        mod_date,            # last mod date
        crc & 0xFFFFFFFF,    # crc-32
        comp_field,          # compressed size (or sentinel)
        uncomp_field,        # uncompressed size (or sentinel)
        len(filename),       # filename length
        len(extra),          # extra field length
    ))
    f.write(filename)
    f.write(extra)


def _write_local_header_placeholder(f, filename: bytes, comp_type: int, mtime: tuple,
                                    uncomp_size: int, need_zip64: bool):
    """Write a local file header with zeroed crc/size fields for streaming.

    Returns ``(header_pos, comp_field_pos, comp_extra_pos)``:
      * ``header_pos``      – absolute offset of the 30-byte header start
      * ``comp_field_pos``  – absolute offset where the 32-bit compressed-size
                               field (or its 0xFFFFFFFF sentinel) lives
      * ``comp_extra_pos``  – absolute offset of the compressed-size entry
                               inside the ZIP64 extra field, or ``None`` when
                               no ZIP64 extra field reserves a slot for it
    """
    if len(mtime) >= 6:
        mod_date = _zip_mod_date(mtime[0], mtime[1], mtime[2])
        mod_time = _zip_mod_time(mtime[3], mtime[4], mtime[5])
    else:
        mod_date, mod_time = 0, 0

    header_pos = f.tell()
    comp_extra_pos = None

    if need_zip64:
        uncomp_field = 0xFFFFFFFF if uncomp_size >= 0xFFFFFFFF else uncomp_size
        comp_field = 0xFFFFFFFF  # compressed size unknown -> sentinel
        version_needed = 45
        # Build extra field up-front; reserve a uint64 slot for the compressed
        # size so the total header length is fixed and we can patch it later.
        payload = bytearray()
        if uncomp_size >= 0xFFFFFFFF:
            payload.extend(struct.pack('<Q', uncomp_size))
        comp_extra_pos = header_pos + 30 + len(filename) + 4 + len(payload)
        payload.extend(struct.pack('<Q', 0))  # compressed size placeholder
        extra = struct.pack('<HH', 0x0001, len(payload)) + bytes(payload)
    else:
        uncomp_field = uncomp_size
        comp_field = 0  # patched later
        extra = b''
        version_needed = 20

    f.write(struct.pack('<IHHHHHIIIHH',
        0x04034B50,
        version_needed,
        0,
        comp_type,
        mod_time,
        mod_date,
        0,                   # crc placeholder
        comp_field,
        uncomp_field,
        len(filename),
        len(extra),
    ))
    f.write(filename)
    f.write(extra)

    comp_field_pos = header_pos + _LFH_CSIZE_OFFSET
    return header_pos, comp_field_pos, comp_extra_pos


def _backfill_local_header(f, header_pos: int, crc: int,
                           comp_size: int, uncomp_size: int,
                           need_zip64: bool, comp_field_pos: int,
                           comp_extra_pos):
    """Patch the real crc / compressed size into a placeholder local header.

    ``comp_extra_pos`` is the value returned by
    :func:`_write_local_header_placeholder` (``None`` when no ZIP64 extra
    slot was reserved for the compressed size).
    """
    # crc-32 (always in the fixed header)
    f.seek(header_pos + _LFH_CRC_OFFSET)
    f.write(struct.pack('<I', crc & 0xFFFFFFFF))

    if need_zip64:
        # 32-bit csize field holds the sentinel; the real value lives in the
        # extra field.  Sentinel is already in place, only patch the extra.
        if comp_extra_pos is not None:
            f.seek(comp_extra_pos)
            f.write(struct.pack('<Q', comp_size))
        # Also ensure the 32-bit usize sentinel is correct (already set at
        # placeholder time; nothing to do when uncomp_size < 4 GiB).
    else:
        # Plain 32-bit fields: patch csize (usize already correct).
        f.seek(comp_field_pos)
        f.write(struct.pack('<I', comp_size))

    f.seek(0, os.SEEK_END)


def _write_cd_entry(f, filename: bytes, crc: int, comp_size: int,
                    uncomp_size: int, comp_type: int, mtime: tuple,
                    header_offset: int, need_zip64: bool = False):
    """Write a central directory record (46 bytes fixed + filename + extra + comment).

    mtime: (year, month, day, hour, minute, second) from time.localtime()[:6]
    need_zip64: when True, overflow 32-bit fields are stored as the
        0xFFFFFFFF sentinel and a ZIP64 extra field (tag 0x0001) is
        appended carrying the real 64-bit sizes and local header offset.
        Otherwise everything is written with plain 32-bit fields.
    """
    if len(mtime) >= 6:
        mod_date = _zip_mod_date(mtime[0], mtime[1], mtime[2])
        mod_time = _zip_mod_time(mtime[3], mtime[4], mtime[5])
    else:
        mod_date, mod_time = 0, 0

    if need_zip64:
        # Sentinel values trigger the reader to consult the ZIP64 extra field.
        comp_field = 0xFFFFFFFF if comp_size >= 0xFFFFFFFF else comp_size
        uncomp_field = 0xFFFFFFFF if uncomp_size >= 0xFFFFFFFF else uncomp_size
        offset_field = 0xFFFFFFFF if header_offset >= 0xFFFFFFFF else header_offset
        extra = _build_zip64_cd_extra(uncomp_size, comp_size, header_offset)
        version_needed = 45  # 4.5 required for ZIP64
    else:
        comp_field = comp_size
        uncomp_field = uncomp_size
        offset_field = header_offset
        extra = b''
        version_needed = 20  # 2.0

    # Central directory record: 46 bytes fixed
    f.write(struct.pack('<IHHHHHHIIIHHHHHII',
        0x02014B50,          # signature
        45,                  # version made by (4.5)
        version_needed,      # version needed
        0,                   # flags
        comp_type,           # compression method
        mod_time,            # last mod time
        mod_date,            # last mod date
        crc & 0xFFFFFFFF,    # crc-32
        comp_field,          # compressed size (or sentinel)
        uncomp_field,        # uncompressed size (or sentinel)
        len(filename),       # filename length
        len(extra),          # extra field length
        0,                   # file comment length
        0,                   # disk number start
        0,                   # internal file attributes
        0,                   # external file attributes
        offset_field,        # relative offset of local header (or sentinel)
    ))
    f.write(filename)
    f.write(extra)


def _write_zip64_end(f, entries: int, central_offset: int, central_size: int):
    """Write the ZIP64 End Of Central Directory record + locator.

    MUST be emitted immediately *before* the standard End Of Central
    Directory record.  Corrects the two fatal bugs of the reference
    implementation:

    * ZIP64 EOCD **record** signature is 0x06064B50 (PK\\x06\\x06).
    * ZIP64 EOCD **locator** signature is 0x07064B50 (PK\\x06\\x07).
    * The locator's "offset of ZIP64 EOCD record" field must point at the
      record's start, not at the locator field itself.
    """
    # Record the start of the ZIP64 EOCD record *before* writing it so the
    # locator can reference it correctly.
    zip64_eocd_offset = f.tell()

    # ---- ZIP64 End Of Central Directory record (sig 0x06064B50) ----
    f.write(struct.pack('<I', 0x06064B50))           # signature
    f.write(struct.pack('<Q', 44))                   # size of fixed fields after this (44)
    f.write(struct.pack('<H', 45))                   # version made by (4.5)
    f.write(struct.pack('<H', 45))                   # version needed to extract (4.5)
    f.write(struct.pack('<I', 0))                    # number of this disk
    f.write(struct.pack('<I', 0))                    # disk with start of central directory
    f.write(struct.pack('<Q', entries))              # entries on this disk
    f.write(struct.pack('<Q', entries))              # total entries
    f.write(struct.pack('<Q', central_size))         # size of central directory
    f.write(struct.pack('<Q', central_offset))       # offset of central directory
    # (no extensible data sector)

    # ---- ZIP64 End Of Central Directory locator (sig 0x07064B50) ----
    f.write(struct.pack('<I', 0x07064B50))           # signature
    f.write(struct.pack('<I', 0))                    # disk with ZIP64 EOCD record
    f.write(struct.pack('<Q', zip64_eocd_offset))    # offset of ZIP64 EOCD record
    f.write(struct.pack('<I', 1))                    # total number of disks


def create_zstd_zip(
    output_path: str,
    file_list: list,
    progress_callback=None,
    compress_level: int = 3,
) -> str:
    """Create a Zstd-compressed ZIP archive (Method 93) by **streaming**.

    Bypasses Python's zipfile module entirely to avoid
    "That compression method is not supported" on Python < 3.14.

    Each source file is compressed in fixed-size chunks through a zstd
    ``compressobj`` and written to disk immediately; only a small amount of
    per-entry metadata (offset / sizes / CRC) is kept in memory for the
    central directory.  Peak memory is therefore a single chunk buffer
    (~1 MiB), independent of file or archive size.

    Supports ZIP64: when any single file's compressed/uncompressed size or
    local-header offset exceeds the 32-bit range, a ZIP64 extra field
    (tag 0x0001) is written for that entry; and when the total number of
    entries, the central-directory size, or its start offset exceed the
    32-bit range, a ZIP64 End Of Central Directory record + locator are
    emitted before the standard EOCD record.

    The reader side (Python ``zipfile``) transparently understands ZIP64,
    so archives produced here are readable by ``zipfile.ZipFile`` and any
    ZIP64-aware tool (7-Zip, etc.).
    """
    zstandard = _get_zstd()
    total = len(file_list)

    # Per-entry metadata for the central directory.  We store *only* scalar
    # fields here – never the file data itself.
    # (filename_bytes, crc, comp_size, uncomp_size, mtime, header_offset, need_zip64)
    cd_entries = []

    with open(output_path, "wb") as f:
        for idx, (src_path, arcname) in enumerate(file_list, 1):
            file_stat = os.stat(src_path)
            uncomp_size = file_stat.st_size
            mtime = _time.localtime(file_stat.st_mtime)[:6]
            filename_bytes = arcname.encode('utf-8')

            header_offset = f.tell()

            # Per-entry ZIP64 trigger: uncompressed size or local-header
            # offset overflow.  The compressed size is, by the nature of
            # compression, <= uncompressed size, so a non-overflowing
            # uncomp_size guarantees comp_size cannot overflow either; when
            # uncomp_size overflows we reserve a ZIP64 extra slot regardless.
            need_zip64_entry = (
                uncomp_size >= 0xFFFFFFFF
                or header_offset >= 0xFFFFFFFF
            )

            # Write the local-file-header placeholder (sizes/CRC zeroed),
            # then stream the compressed payload after it.
            header_pos, comp_field_pos, comp_extra_pos = \
                _write_local_header_placeholder(
                    f, filename_bytes, 93, mtime, uncomp_size,
                    need_zip64=need_zip64_entry,
                )

            # Stream-compress the source file: read chunk -> update CRC of
            # the *uncompressed* data -> feed to compressor -> write
            # compressed output to disk immediately.  Memory use is bounded
            # by the chunk size.
            cctx = zstandard.ZstdCompressor(level=compress_level)
            cobj = cctx.compressobj()
            crc = 0
            comp_size = 0
            with open(src_path, "rb") as src:
                while True:
                    chunk = src.read(_ZIP_STREAM_CHUNK)
                    if not chunk:
                        break
                    crc = _zlib.crc32(chunk, crc) & 0xFFFFFFFF
                    out = cobj.compress(chunk)
                    if out:
                        f.write(out)
                        comp_size += len(out)
                tail = cobj.flush()
                if tail:
                    f.write(tail)
                    comp_size += len(tail)
            crc &= 0xFFFFFFFF

            # If the streamed compressed size unexpectedly overflowed 4 GiB
            # while we predicted no ZIP64, the local header has no room for
            # the ZIP64 extra field.  Compression cannot expand data beyond
            # ~0.1% worst case for already-incompressible input, so for a
            # sub-4 GiB source this is impossible in practice; guard anyway.
            if comp_size >= 0xFFFFFFFF and not need_zip64_entry:
                raise RuntimeError(
                    f"compressed size for '{arcname}' exceeded 4 GiB but the "
                    "local header was written without a ZIP64 extra field"
                )

            # Backfill the real crc / compressed size into the placeholder.
            _backfill_local_header(
                f, header_pos, crc, comp_size, uncomp_size,
                need_zip64=need_zip64_entry,
                comp_field_pos=comp_field_pos,
                comp_extra_pos=comp_extra_pos,
            )

            cd_entries.append((filename_bytes, crc, comp_size, uncomp_size,
                               mtime, header_offset, need_zip64_entry))

            if progress_callback is not None:
                progress_callback(idx, total, arcname)

        # ---- Write central directory (metadata only, no file data) ----
        cd_start = f.tell()
        cd_size = 0
        for (filename_bytes, crc, comp_size, uncomp_size, mtime,
             header_offset, need_zip64_entry) in cd_entries:
            before = f.tell()
            _write_cd_entry(f, filename_bytes, crc, comp_size, uncomp_size, 93,
                            mtime, header_offset, need_zip64=need_zip64_entry)
            cd_size += f.tell() - before

        # ---- Archive-level ZIP64 trigger ----
        need_zip64_archive = (
            len(cd_entries) >= 0xFFFF
            or cd_size >= 0xFFFFFFFF
            or cd_start >= 0xFFFFFFFF
        )
        if need_zip64_archive:
            _write_zip64_end(f, len(cd_entries), cd_start, cd_size)

        # ---- Standard End Of Central Directory ----
        # In the ZIP64 case the count/size/offset fields are clamped to the
        # 0xFFFF / 0xFFFFFFFF sentinels so a ZIP64-aware reader is directed
        # to the ZIP64 EOCD record written above.
        f.write(struct.pack('<IHHHHIIH',
            0x06054B50,                       # signature
            0,                                # number of this disk
            0,                                # disk where CD starts
            min(len(cd_entries), 0xFFFF),     # number of CD records on this disk
            min(len(cd_entries), 0xFFFF),     # total number of CD records
            min(cd_size, 0xFFFFFFFF),         # size of central directory
            min(cd_start, 0xFFFFFFFF),        # offset of start of central directory
            0,                                # .zip file comment length
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
