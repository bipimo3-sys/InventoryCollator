# Phase 1 — Inventory Scanning Workflow

**Status:** Implementation-Grade Specification  
**Scope:** Filesystem Inventory + Audio Detection + Metadata Extraction  
**Modifies Files:** ❌ No  
**Moves Files:** ❌ No  
**Groups Artists:** ❌ No  
**Duplicate Detection:** ❌ Not in this phase

---

## Overview

Phase 1 performs **only** the following:

- Detect drive
- Register `drive_key`
- Scan filesystem
- Identify audio files
- Extract metadata
- Compute partial hash
- Store everything in DB
- Handle resume safely

It explicitly does **NOT**:

- Group artists
- Detect duplicates (beyond storing hashes)
- Move files
- Modify tags

This phase produces a **pure archival snapshot** of the drive.

---

# Step 0 — App Startup

### Input Parameters

```
--rescan-mode=skip|force
--compute-full-hash=false|true
--audio-extensions=default|custom_list
```

### Default Values

```
rescan-mode = skip
compute-full-hash = false
extension whitelist = predefined set
```

---

# Step 1 — Detect Connected Drive

1. List mounted drives.
2. User selects drive letter.
3. App checks root for:

```
\.__MUSIC_ARCHIVE_DRIVE_ID
```

---

## Case A — Key File Exists

1. Read JSON.
2. Extract `drive_key`.
3. Lookup in database.

### If Exists in DB

- Update `last_seen_at`
- Update `free_bytes`
- Update `total_bytes`

### If Not Exists in DB

- Register new drive row using existing `drive_key`

---

## Case B — Key File Missing

Prompt user:

```
1. Register as new drive?
2. Abort?
```

If register:

- Generate UUID `drive_key`
- Create key file
- Insert drive into DB

---

# Step 2 — Pre-Scan Housekeeping

Before scanning:

```sql
UPDATE files
SET scan_status = 'not_seen'
WHERE drive_id = ?;
```

Purpose:

- Allows detection of deleted files after scan

---

# Step 3 — Filesystem Crawl

- Single-threaded
- Depth-first traversal

For each file encountered:

---

## 3.1 Normalize Path

- Compute `relative_path`
- Extract `parent_path`
- Compute `depth`
- Extract lowercase `extension`

---

## 3.2 Check If Already Known

```sql
SELECT id, size_bytes, modified_at
FROM files
WHERE drive_id = ?
AND relative_path = ?;
```

### If Exists

If:

- `rescan-mode == skip`
- `size_bytes unchanged`
- `modified_at unchanged`

Then:

- Update `last_seen_at`
- Update `scan_status = 'unchanged'`
- CONTINUE

Else:

- Proceed to reprocess file

### If Not Exists

- Insert new row
- `scan_status = 'new'`

---

# Step 4 — Audio Detection

## 4.1 Extension Whitelist

Default whitelist:

```
mp3
flac
wav
aiff
ogg
m4a
aac
ape
alac
wma
```

If extension not in whitelist:

- `is_audio = 0`
- `scan_status = 'non_audio'`
- Continue

---

## 4.2 Header Validation

Attempt:

- Open file
- Use metadata parser for extension

If parser fails:

- `is_audio = 0`
- `scan_status = 'invalid_audio'`
- Continue

If valid:

- `is_audio = 1`

---

# Step 5 — Store Physical File Data

Insert or update:

- `size_bytes`
- `created_at`
- `modified_at`
- `extension`
- `parent_path`
- `depth`
- `first_seen_at` (if new)
- `last_seen_at` (always)
- `scan_status = 'audio_detected'`

---

# Step 6 — Store Path Components

Split `relative_path` into components.

For each component:

- Insert into `file_path_components`
- `position` index = `0..N`

Purpose:

- Enables future folder inference

---

# Step 7 — Extract Audio Metadata

Use format-aware reader.

Extract:

- `tag_artist`
- `tag_album`
- `tag_title`
- `tag_album_artist`
- `tag_genre`
- `tag_year`
- `tag_track_number`
- `tag_disc_number`
- `tag_composer`
- `tag_comment`
- `tag_encoder`

Store full raw metadata JSON.

If metadata extraction fails:

- Keep file
- `scan_status = 'audio_no_metadata'`

---

# Step 8 — Compute Partial Hash

Hash strategy:

```
partial_hash = SHA256(
    first 8MB of file
    + file_size
)
```

Store in:

```
files.partial_hash
```

If `--compute-full-hash=true`:

- Compute `full_hash`

Else:

- `full_hash = NULL`

---

# Step 9 — Mark Scan Complete

Set:

```
scan_status = 'complete'
```

Commit transaction periodically:

- Every 100 files (recommended)

---

# Step 10 — Post-Scan Cleanup

After full crawl:

Find rows:

```sql
WHERE drive_id = ?
AND scan_status = 'not_seen';
```

These files no longer exist physically.

### Default Behavior

- Set `scan_status = 'missing'`
- Do NOT delete row automatically

---

# Step 11 — Drive Free Space Update

Update:

- `free_bytes`
- `total_bytes`
- `last_seen_at`

---

# Step 12 — Final Report Output

Display:

- Total files scanned
- Total audio files
- New files
- Modified files
- Missing files
- Invalid audio files
- Metadata extraction failures
- Total bytes processed

---

# Failure Handling Rules

For any exception:

- Catch per file
- Log error in `scan_status`
- Continue scanning
- Never abort entire process

---

# Resume Behavior

If scan interrupted:

On next run:

- Files with `scan_status != 'complete'`
  will be reprocessed

Skip-mode only applies when:

- `size_bytes` match
- `modified_at` match

---

# Performance Expectation

On spinning external HDD:

Expected:

- 80–150 MB/s sequential read
- Metadata extraction: minimal CPU-bound overhead

50 TB full scan:

- Several days (first run only)

Future scans:

- Fast due to skip-mode

---

# Phase 1 Output Guarantee

After Phase 1 completes, you will have:

- Complete physical inventory
- Structured folder hierarchy
- Audio metadata extracted
- Partial hashes stored
- Accurate file presence tracking
- Stable drive identity
- No file modifications performed

This phase produces a **safe, pure archival snapshot**.
