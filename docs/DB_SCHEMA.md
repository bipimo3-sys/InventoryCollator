# InventoryCollator Database Schema

**Version:** Production Final  
**Database:** SQLite  
**Target Scale:** 30–50 TB  
**Architecture:** Single unified database using drive_key identity

---

## Design Principles

- Uses `drive_key` identity via root key file
- Stores relative paths only
- Separates physical state from embedded metadata
- Preserves folder structure as structured components
- Supports duplicate detection
- Supports planning and execution journaling
- Supports full rollback
- Optimized for large-scale storage
- SQLite-ready

---

## Core Tables

### drives

```sql
CREATE TABLE drives (
    id INTEGER PRIMARY KEY,
    drive_key TEXT UNIQUE NOT NULL,
    volume_serial TEXT,
    label TEXT,
    first_registered_at DATETIME,
    last_seen_at DATETIME,
    total_bytes INTEGER,
    free_bytes INTEGER,
    status TEXT
);

CREATE INDEX idx_drives_key ON drives(drive_key);
```

### files (Physical Layer)

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    drive_id INTEGER NOT NULL,
    relative_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    extension TEXT,
    parent_path TEXT,
    depth INTEGER,
    size_bytes INTEGER,
    created_at DATETIME,
    modified_at DATETIME,
    first_seen_at DATETIME,
    last_seen_at DATETIME,
    partial_hash TEXT,
    full_hash TEXT,
    audio_fingerprint TEXT,
    is_audio BOOLEAN,
    scan_status TEXT,
    FOREIGN KEY (drive_id) REFERENCES drives(id)
);

CREATE INDEX idx_files_drive ON files(drive_id);
CREATE INDEX idx_files_partial_hash ON files(partial_hash);
CREATE INDEX idx_files_full_hash ON files(full_hash);
CREATE INDEX idx_files_is_audio ON files(is_audio);
```

### file_path_components (Structured Folder Data)

```sql
CREATE TABLE file_path_components (
    file_id INTEGER,
    position INTEGER,
    component TEXT,
    PRIMARY KEY (file_id, position),
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX idx_path_components_file ON file_path_components(file_id);
```

### file_audio_metadata (Embedded Tags)

```sql
CREATE TABLE file_audio_metadata (
    file_id INTEGER PRIMARY KEY,
    format_type TEXT,
    tag_artist TEXT,
    tag_album TEXT,
    tag_title TEXT,
    tag_album_artist TEXT,
    tag_genre TEXT,
    tag_year TEXT,
    tag_track_number TEXT,
    tag_disc_number TEXT,
    tag_composer TEXT,
    tag_comment TEXT,
    tag_encoder TEXT,
    raw_tag_json TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id)
);
```

---

## Identification Layer

### artists (Normalized Identity)

```sql
CREATE TABLE artists (
    id INTEGER PRIMARY KEY,
    normalized_name TEXT UNIQUE,
    display_name TEXT,
    genre_1 TEXT,
    genre_2 TEXT,
    genre_3 TEXT,
    genre_source TEXT,
    is_various_artists BOOLEAN DEFAULT 0,
    image_status TEXT,
    image_file_name TEXT
);

CREATE INDEX idx_artists_normalized ON artists(normalized_name);
```

### artist_aliases (Raw Evidence Variations)

```sql
CREATE TABLE artist_aliases (
    id INTEGER PRIMARY KEY,
    artist_id INTEGER,
    alias_name TEXT,
    confidence_score REAL,
    source TEXT,
    FOREIGN KEY (artist_id) REFERENCES artists(id)
);
```

### albums

```sql
CREATE TABLE albums (
    id INTEGER PRIMARY KEY,
    artist_id INTEGER,
    normalized_name TEXT,
    display_name TEXT,
    year TEXT,
    source_confidence REAL,
    FOREIGN KEY (artist_id) REFERENCES artists(id)
);

CREATE INDEX idx_albums_artist ON albums(artist_id);
```

### tracks (Derived Identification Layer)

```sql
CREATE TABLE tracks (
    id INTEGER PRIMARY KEY,
    file_id INTEGER UNIQUE,
    artist_id INTEGER,
    album_id INTEGER,
    detected_artist TEXT,
    detected_album TEXT,
    detected_title TEXT,
    identification_method TEXT,
    confidence_score REAL,
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (artist_id) REFERENCES artists(id),
    FOREIGN KEY (album_id) REFERENCES albums(id)
);

CREATE INDEX idx_tracks_artist ON tracks(artist_id);
CREATE INDEX idx_tracks_album ON tracks(album_id);
```

---

## Duplicate Detection

### duplicate_groups

```sql
CREATE TABLE duplicate_groups (
    id INTEGER PRIMARY KEY,
    duplicate_type TEXT,
    confidence_score REAL,
    resolution_status TEXT
);
```

### duplicate_members

```sql
CREATE TABLE duplicate_members (
    group_id INTEGER,
    file_id INTEGER,
    PRIMARY KEY (group_id, file_id),
    FOREIGN KEY (group_id) REFERENCES duplicate_groups(id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);
```

---

## Planning Layer

### artist_drive_plan (ARTIST DRIVE ALLOCATION PLAN)

```sql
CREATE TABLE artist_drive_plan (
    artist_id INTEGER PRIMARY KEY,
    target_drive_id INTEGER,
    target_folder_name TEXT,
    estimated_total_size INTEGER,
    free_space_check_passed BOOLEAN,
    approval_status TEXT,
    FOREIGN KEY (artist_id) REFERENCES artists(id),
    FOREIGN KEY (target_drive_id) REFERENCES drives(id)
);
```

### file_move_plan

```sql
CREATE TABLE file_move_plan (
    id INTEGER PRIMARY KEY,
    file_id INTEGER,
    source_drive_id INTEGER,
    source_relative_path TEXT,
    target_drive_id INTEGER,
    target_relative_path TEXT,
    operation_type TEXT,
    requires_copy_suffix BOOLEAN,
    execution_status TEXT,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (source_drive_id) REFERENCES drives(id),
    FOREIGN KEY (target_drive_id) REFERENCES drives(id)
);

CREATE INDEX idx_move_status ON file_move_plan(execution_status);
```

---

## Execution & Recovery

### execution_log (EXECUTION JOURNAL)

```sql
CREATE TABLE execution_log (
    id INTEGER PRIMARY KEY,
    move_plan_id INTEGER,
    action TEXT,
    action_timestamp DATETIME,
    status TEXT,
    checksum_before TEXT,
    checksum_after TEXT,
    FOREIGN KEY (move_plan_id) REFERENCES file_move_plan(id)
);
```

### drive_file_state (Recovery Handling)

```sql
CREATE TABLE drive_file_state (
    drive_id INTEGER,
    file_id INTEGER,
    is_valid BOOLEAN,
    invalidated_reason TEXT,
    PRIMARY KEY (drive_id, file_id),
    FOREIGN KEY (drive_id) REFERENCES drives(id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);
```

---

## Special Reserved Artist Row

During initialization insert:

```
normalized_name = 'va'
display_name = 'Various Artists'
is_various_artists = 1
```
