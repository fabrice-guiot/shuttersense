# AI Integration Roadmap — Image Intelligence for ShutterSense

**Status**: Proposal
**Created**: 2026-02-18
**Related Documents**:
- [MCP Server Integration PRD](prd/000-mcp-server-integration.md)
- [Architecture](architecture.md)
- [Distributed Agent Architecture PRD](prd/021-distributed-agent-architecture.md)
- [Pipeline-Driven Analysis Tools PRD](prd/217-pipeline-driven-analysis-tools.md)

---

## Executive Summary

ShutterSense currently performs all analysis based on filenames, file metadata, and file presence — it never examines what is *inside* the photos. This document proposes a phased roadmap for integrating AI-powered image intelligence into the platform, transforming ShutterSense from a collection management and workflow validation tool into a content-aware photo intelligence system.

These integrations are designed to:

- Work within the existing **agent-based execution architecture** (analysis runs where the photos live)
- Store results in the established **JSONB result format** with trend support
- Expose through both the **web UI** and the **MCP server** for natural-language interaction
- Respect photographer workflows — augment, don't replace, existing curation tools

### The Gap

| What ShutterSense Knows Today | What It Could Know |
|-------------------------------|-------------------|
| File exists at path X | What the photo depicts |
| File is 24.7 MB, .cr3 extension | Shot at f/2.8, 1/500s, ISO 800 with a 70-200mm lens |
| Filename says "HDR" | Image has high dynamic range, well-exposed, tack sharp |
| Photo AB3D0042 has a pair AB3D0042-2 | Both photos show the same performer from different angles |
| Pipeline path was followed correctly | The output quality meets professional standards |
| Event "Jazz Festival" had 3,200 photos | 40% crowd, 30% performer close-ups, 20% wide stage, 10% detail/macro |

---

## Architectural Principles

All AI integrations follow these constraints:

1. **Agent-executed**: Image processing runs on agents, not the server. Agents have local filesystem access and potential GPU availability. The server remains a coordinator.
2. **Opt-in per collection**: AI analysis tools are pipeline-configurable, not automatically applied. Photographers control what runs and when.
3. **Incremental processing**: Only analyze new/changed images. Use existing `input_state_hash` and storage optimization patterns.
4. **Result composability**: AI-generated metadata feeds into existing tools. Quality scores enhance pipeline validation. Embeddings enable search through MCP. Tags enrich trend analysis.
5. **Privacy-conscious**: No image data leaves the agent unless the user explicitly configures a cloud AI provider. Local-first inference is always available.
6. **Cost-aware**: Cloud vision APIs are expensive at scale. Provide sampling strategies, tiered processing, and clear cost estimates before execution.

---

## Phase 1: EXIF & Metadata Deep Analysis

**Priority**: Highest — foundational for all subsequent phases
**Complexity**: Low
**New dependencies**: `Pillow` or `pyexiv2` (Python), optionally `exiftool` (subprocess)

### Current State

ShutterSense tracks XMP sidecar files (presence/absence) but never reads EXIF data from images. Camera identification relies entirely on filename-encoded 4-character camera IDs. No lens, exposure, GPS, or color profile data is extracted.

### Proposed Capabilities

#### 1.1 Shooting Parameter Extraction

Extract core EXIF fields from every image during `photostats` or `photo_pairing` runs:

| EXIF Field | Use Case |
|-----------|----------|
| Camera Make/Model/Serial | Auto-populate `cameras` table, validate against filename camera_id |
| Lens Model/Focal Length | Lens usage statistics, focal length distribution per event |
| Aperture, Shutter Speed, ISO | Exposure pattern analysis, shooting style profiling |
| Metering Mode, Flash | Technique usage trends |
| Date/Time Original + Offset | Timestamp-based timeline reconstruction, shooting rate analysis |
| GPS Coordinates | Auto-correlate photos to event locations (geocoding service already exists) |
| Color Space, White Balance | Processing pipeline input validation |
| Image Dimensions | Resolution tracking, crop detection |
| Software | Identify which processing tools were used (Lightroom, Capture One, etc.) |

#### 1.2 EXIF-Enriched Analytics

New statistics available after EXIF extraction:

- **Lens usage distribution**: Focal length histogram per collection/event
- **Exposure analysis**: ISO distribution, shutter speed ranges, aperture preferences
- **Shooting timeline**: Photos-per-minute rate, gap detection, peak activity periods
- **Camera-to-EXIF validation**: Does filename camera_id match EXIF serial number?
- **GPS clustering**: Group photos by physical location within a collection

#### 1.3 Architecture

```
Agent (during analysis run)
  │
  ├─ Read EXIF from image files (Pillow/pyexiv2)
  ├─ Extract standardized field set
  ├─ Aggregate per-collection statistics
  │
  └─ Report to server as part of existing result JSONB
       │
       ├─ New "exif_stats" section in photostats results
       ├─ Camera table auto-enrichment (make, model, serial)
       └─ GPS coordinates → event location correlation
```

#### 1.4 MCP Integration

New MCP capabilities enabled:
- "What lenses did I use most at the jazz festival?"
- "Show me my ISO distribution — am I shooting too high?"
- "Which photos from this collection were taken within 1km of the venue?"

---

## Phase 2: CLIP Embeddings for Semantic Search & Similarity

**Priority**: Very High — highest-leverage AI integration
**Complexity**: Medium
**New dependencies**: `open-clip-torch` or `transformers` (agent), `pgvector` extension (PostgreSQL)

### Rationale

This is the single most transformative integration because it enables an entirely new interaction paradigm. Instead of navigating pages and filters, users describe what they want in natural language and the system finds matching photos across their entire portfolio. Combined with the MCP server, this turns ShutterSense into a conversational photo search engine.

### Proposed Capabilities

#### 2.1 Embedding Generation

Generate a 512/768-dimensional vector embedding for each image using CLIP (or SigLIP/OpenCLIP):

- **Local inference on agents**: CLIP runs efficiently on CPU (~50-100ms/image). No cloud API needed.
- **Batch processing**: Generate embeddings during a dedicated analysis run or as a post-step after `photo_pairing`.
- **Incremental updates**: Only embed new images (track via `input_state_hash`).
- **Storage**: `pgvector` column on a new `image_embeddings` table, or sidecar storage.

#### 2.2 Search Capabilities

| Search Type | Description | Example |
|------------|-------------|---------|
| Text-to-image | Natural language → matching photos | "sunset over mountains with silhouettes" |
| Image-to-image | Similar photos across collections | "find shots similar to this one" |
| Cluster analysis | Group visually similar photos | Auto-organize by visual theme |
| Outlier detection | Flag photos that don't fit | "this photo doesn't belong in this collection" |
| Cross-collection discovery | Find related content across portfolio | "similar compositions across all events" |

#### 2.3 Near-Duplicate Detection

Beyond filename-based pairing, identify visually identical or near-identical images:

- Detect unintentional duplicates across collections
- Find re-processed versions of the same shot
- Identify burst sequences that filename patterns missed
- Storage waste estimation for duplicates

#### 2.4 Architecture

```
Agent (embedding generation)                Server (search & storage)
  │                                            │
  ├─ Load CLIP model (cached locally)          ├─ pgvector extension
  ├─ Process images in batches                 ├─ image_embeddings table
  ├─ Generate 512-dim vectors                  ├─ HNSW or IVFFlat index
  │                                            ├─ Cosine similarity search
  └─ Upload embeddings to server               └─ Cluster computation (periodic)
                                                    │
                                               MCP Tools
                                                ├─ search_photos_by_description
                                                ├─ find_similar_photos
                                                └─ detect_duplicates
```

#### 2.5 Database Schema (Sketch)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE image_embeddings (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    collection_id INTEGER NOT NULL REFERENCES collections(id),
    file_path TEXT NOT NULL,
    file_hash TEXT,                          -- For dedup/change detection
    embedding vector(512) NOT NULL,          -- CLIP embedding
    model_version TEXT NOT NULL,             -- e.g., "ViT-B/32"
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(collection_id, file_path)
);

CREATE INDEX idx_embeddings_vector ON image_embeddings
    USING hnsw (embedding vector_cosine_ops);
```

#### 2.6 MCP Integration

New MCP tools:
- `search_photos`: "Find all golden-hour portraits from last month's events"
- `find_similar`: "Show me photos similar to res_abc123's cover shot"
- `detect_duplicates`: "Are there duplicate images across my festival collections?"

---

## Phase 3: Image Quality Assessment (IQA)

**Priority**: High
**Complexity**: Medium
**New dependencies**: `torch` + IQA model weights (agent), or lightweight OpenCV-based heuristics

### Rationale

Photographers spend significant time evaluating technical quality. Automated IQA provides objective quality scores that enhance pipeline validation, enable smart culling, and surface quality trends over time.

### Proposed Capabilities

#### 3.1 Technical Quality Metrics

Two tiers of quality assessment:

**Tier A — Heuristic (no ML, fast, always available):**

| Metric | Method | Use Case |
|--------|--------|----------|
| Sharpness | Laplacian variance | Flag blurry/out-of-focus shots |
| Exposure | Histogram analysis (clipping %) | Detect under/overexposure |
| Noise estimate | High-frequency energy analysis | Flag high-ISO noise |
| Dynamic range | Histogram spread | Validate HDR processing |
| Color cast | Channel mean deviation | Detect white balance issues |

**Tier B — ML-based (requires model weights, higher accuracy):**

| Model | Output | Notes |
|-------|--------|-------|
| MUSIQ | Aesthetic score (1-100) | Multi-scale, no fixed input size |
| NIMA | Mean opinion score + distribution | Well-studied, lightweight |
| DBCNN | Technical + aesthetic scores | Dual-branch, good for both dimensions |

#### 3.2 Quality-Enhanced Pipeline Validation

Integrate quality scores into pipeline validation results:

- Per-termination-path quality distribution: "HDR path averages 78/100, single-exposure averages 62/100"
- Quality gates: Flag images below configurable threshold as pipeline warnings
- Quality trends over time: "Collection quality has improved 12% since adopting the new workflow"

#### 3.3 Per-Group Quality Ranking

Within each pairing group (images sharing camera_id + counter):

- Rank images by composite quality score
- Identify the "hero" shot per group
- Flag groups where all images are below threshold

#### 3.4 Architecture

```
Agent (quality analysis run)
  │
  ├─ Tier A: OpenCV/numpy heuristics (always available, ~10ms/image)
  ├─ Tier B: PyTorch model inference (optional, ~50-200ms/image)
  │
  ├─ Per-image scores stored in result JSONB
  ├─ Per-group rankings computed
  └─ Aggregated quality statistics per collection
       │
       Server
       ├─ Quality trends (new dimension in trend_service)
       ├─ Pipeline validation quality overlay
       └─ MCP: "What's the average quality in my latest import?"
```

#### 3.5 New Tool Type

Register `image_quality` as a new analysis tool:

- Configurable tier (A only, A+B)
- Configurable quality threshold for warnings
- Sampling mode for large collections (analyze every Nth image, or random sample)
- Results feed into existing trend aggregation

---

## Phase 4: Vision-Language Model Content Classification

**Priority**: High
**Complexity**: Medium
**New dependencies**: Cloud API client (Anthropic/OpenAI/Google), or local model (LLaVA, moondream)

### Rationale

Understanding photo *content* at a semantic level enables coverage analysis for events, automated tagging, and richer natural-language interaction through MCP. This is particularly valuable for event photographers who need to verify they captured all required shot types.

### Proposed Capabilities

#### 4.1 Scene Classification & Auto-Tagging

Use a vision-language model to classify each photo:

| Tag Category | Examples | Use Case |
|-------------|----------|----------|
| Scene type | landscape, portrait, action, macro, architecture, street | Collection composition analysis |
| Subject | performer, crowd, venue, equipment, food, signage | Event coverage verification |
| Composition | wide, medium, close-up, detail, overhead, low-angle | Shot variety analysis |
| Mood/Lighting | golden hour, blue hour, dramatic, flat, backlit, silhouette | Aesthetic trend tracking |
| Activity | performing, speaking, dancing, posing, candid | Event narrative coverage |

#### 4.2 Event Coverage Analysis

For collections linked to events, analyze whether required shot types were captured:

```
Event: "Jazz Festival 2026"
Coverage Report:
  ✓ Wide establishing shots: 45 photos (15%)
  ✓ Performer close-ups: 89 photos (30%)
  ✓ Crowd/atmosphere: 120 photos (40%)
  ⚠ Detail/macro: 12 photos (4%) — below recommended 10%
  ⚠ Venue exterior: 3 photos (1%) — consider adding
  ✓ Backstage/candid: 31 photos (10%)
```

#### 4.3 Sampling Strategy

Processing every image through a vision API is cost-prohibitive at scale. Recommended approach:

1. **Representative sampling**: Select 1 image per pairing group (the "hero" from IQA ranking)
2. **Cluster-based sampling**: After CLIP embedding (Phase 2), sample from each visual cluster
3. **On-demand deep analysis**: Full classification triggered manually for specific collections
4. **Local model option**: Run LLaVA or moondream on-agent for zero API cost (lower accuracy, higher compute)

#### 4.4 Cost Modeling

| Approach | Cost per 1,000 images | Accuracy | Latency |
|----------|----------------------|----------|---------|
| Claude (sampled, 1-in-5) | ~$2.00 | Highest | ~2s/image |
| GPT-4V (sampled, 1-in-5) | ~$2.50 | High | ~3s/image |
| Local LLaVA-7B | $0.00 | Medium | ~1s/image (GPU) |
| Local moondream | $0.00 | Medium-Low | ~0.3s/image (CPU) |

#### 4.5 MCP Integration

Rich natural-language queries become possible:
- "How was my coverage at the jazz festival? Did I miss any shot types?"
- "What percentage of my portfolio is portraits vs. landscapes?"
- "Tag all photos from last weekend's event"

---

## Phase 5: Automated Culling & Best-Shot Selection

**Priority**: High (major photographer workflow improvement)
**Complexity**: Medium
**Dependencies**: Phase 1 (EXIF) + Phase 3 (IQA), optionally Phase 4 (content classification)

### Rationale

For photographers shooting burst sequences, bracketed exposures, or high-volume events, selecting the best frame from each group is a major time sink. Automated culling suggestions can save hours per event.

### Proposed Capabilities

#### 5.1 Composite Scoring

Combine multiple signals into a per-image cull score:

| Signal | Weight | Source |
|--------|--------|--------|
| Sharpness score | 30% | Phase 3 (IQA) |
| Exposure quality | 20% | Phase 3 (IQA) + Phase 1 (EXIF histogram) |
| Face sharpness (if faces present) | 20% | Phase 6 (Face Detection) |
| Compositional uniqueness | 15% | Phase 2 (CLIP — distance from group centroid) |
| Technical metadata quality | 15% | Phase 1 (EXIF — optimal ISO, shutter for focal length) |

#### 5.2 Cull Categories

For each image in a pairing group, assign a recommendation:

| Category | Criteria | UI Treatment |
|----------|----------|-------------- |
| **Pick** | Highest composite score in group | Green star |
| **Review** | Within 15% of best score, or unique content | Yellow dot |
| **Reject** | Below quality threshold AND similar to a better shot | Red X |

#### 5.3 New Tool Type

Register `smart_cull` as a new analysis tool:

- Runs after `photo_pairing` (requires pairing groups)
- Configurable scoring weights
- Configurable reject threshold
- Output: per-group recommendations with score breakdowns
- Results integrate with pipeline validation views

#### 5.4 MCP Integration

- `get_cull_suggestions`: "Which photos should I keep from the concert shoot?"
- `get_group_ranking`: "Show me the best shot from each group in collection X"
- "How many photos can I safely reject from this import?"

---

## Phase 6: Face Detection

**Priority**: Medium
**Complexity**: Low
**New dependencies**: `mediapipe` (agent, ~30MB, runs on CPU)

### Important: Detection, Not Recognition

This phase proposes **face detection** (are there faces? how many?) — not **face recognition** (whose face is it?). Recognition raises significant legal concerns (GDPR Art. 9, Illinois BIPA, etc.) and is explicitly out of scope unless a future phase addresses consent workflows.

### Proposed Capabilities

#### 6.1 Face Metrics

| Metric | Description | Use Case |
|--------|-------------|----------|
| Face count | Number of faces detected | People density, portrait vs. crowd |
| Face size (% of frame) | Relative size of largest face | Close-up vs. environmental portrait |
| Face sharpness | Focus quality on detected faces | Cull scoring input (Phase 5) |
| Face positions | Bounding box coordinates | Composition analysis (rule of thirds) |

#### 6.2 Content Classification Enhancement

Face detection enriches Phase 4 content classification:

- 0 faces → likely landscape, architecture, detail, or equipment shot
- 1-2 faces, large → portrait or performer close-up
- 3-10 faces → small group, backstage, meet-and-greet
- 10+ faces → crowd, audience, wide venue shot

#### 6.3 Architecture

```
Agent (during quality or content analysis)
  │
  ├─ MediaPipe Face Detection (CPU, ~5ms/image)
  ├─ Extract: count, bounding boxes, confidence scores
  ├─ Compute: face sharpness (Laplacian on face crops)
  │
  └─ Store in result JSONB alongside quality/content data
```

#### 6.4 Privacy Safeguards

- No face embeddings stored (prevents retroactive identification)
- No face clustering across images
- Only aggregate counts and bounding box coordinates persisted
- Face crop data used transiently for sharpness scoring, then discarded
- Team-level setting to disable face detection entirely

---

## Phase 7: Lightroom & Capture One Catalog Integration

**Priority**: Medium
**Complexity**: Medium
**New dependencies**: `sqlite3` (stdlib, for Lightroom `.lrcat` files), format parsers for Capture One

### Rationale

Many professional photographers already use Lightroom or Capture One for per-image curation. These tools assign star ratings, color labels, keywords, and smart collection groupings. Importing this metadata avoids duplicate analysis effort and bridges ShutterSense's collection-level intelligence with per-image editing tool data.

### Proposed Capabilities

#### 7.1 Lightroom Classic Catalog Import

Lightroom Classic stores its catalog in a SQLite database (`.lrcat`):

| Lightroom Data | ShutterSense Use |
|---------------|-----------------|
| Star ratings (0-5) | Pre-existing quality ranking, skip IQA for rated images |
| Color labels | Workflow stage tracking (e.g., red=rejected, green=approved) |
| Keywords/Tags | Content classification enrichment |
| Collections/Smart Collections | Mapping to ShutterSense collections |
| Develop settings applied | Processing method validation against pipeline |
| Pick/Reject flags | Pre-existing cull decisions |
| GPS (from Lightroom Map module) | Location enrichment |

#### 7.2 Capture One Session/Catalog Import

Capture One uses a different structure (`.cosessiondb` / `.cocatalogdb`):

| Capture One Data | ShutterSense Use |
|-----------------|-----------------|
| Star ratings | Quality ranking |
| Color tags | Workflow tracking |
| Keywords | Content classification |
| Process recipes applied | Pipeline path validation |
| Variants | Processing method tracking |

#### 7.3 Architecture

```
New connector type: CATALOG (alongside S3, GCS, SMB)
  │
  ├─ Catalog file path configured in connector
  ├─ Agent reads catalog database locally
  ├─ Extracts metadata per image file path
  │
  └─ Metadata merged with ShutterSense analysis results
       │
       ├─ Pre-rated images skip quality assessment
       ├─ Keywords enrich content tags
       ├─ Star ratings feed into trend analysis
       └─ Develop settings validate pipeline compliance
```

#### 7.4 MCP Integration

- "Import my Lightroom ratings for the festival collection"
- "How do my Lightroom picks compare to the AI quality scores?"
- "Which photos did Lightroom flag as rejected that the AI rates highly?"

---

## Implementation Phasing

### Dependency Graph

```
Phase 1: EXIF ──────────┬──────────────────────────────────┐
                         │                                  │
Phase 2: CLIP ───────────┤                                  │
                         │                                  │
Phase 3: IQA ────────────┼──── Phase 5: Smart Cull ────────┤
                         │         (requires 1 + 3,         │
Phase 4: Vision-LLM ────┘          optionally 2 + 6)       │
                                                            │
Phase 6: Face Detection ────────────────────────────────────┘

Phase 7: Catalog Integration ── (independent, can start anytime)
```

### Recommended Timeline

| Phase | Name | Depends On | Estimated Scope | Suggested Sequence |
|-------|------|------------|-----------------|-------------------|
| 1 | EXIF Deep Analysis | None | Small-Medium | **Start first** |
| 2 | CLIP Embeddings | None (pgvector setup) | Medium | Start after Phase 1 or in parallel |
| 3 | Image Quality Assessment | None (benefits from Phase 1) | Medium | After Phase 1 |
| 4 | Vision-LLM Classification | Phase 2 (for sampling) | Medium | After Phase 2 |
| 5 | Automated Culling | Phase 1 + Phase 3 | Medium | After Phase 3 |
| 6 | Face Detection | None | Small | Anytime (low effort) |
| 7 | Catalog Integration | None | Medium | Anytime (independent) |

### Integration with MCP Server

Each phase adds new capabilities to the MCP server. The MCP PRD (Phase 4: Resources & Prompts) should be updated as each AI integration phase completes:

| AI Phase | New MCP Tools | New MCP Resources |
|----------|--------------|-------------------|
| Phase 1 | `get_exif_stats`, `get_shooting_timeline` | `shuttersense://collections/{guid}/exif` |
| Phase 2 | `search_photos`, `find_similar`, `detect_duplicates` | `shuttersense://search/embeddings` |
| Phase 3 | `get_quality_report`, `get_quality_trends` | `shuttersense://collections/{guid}/quality` |
| Phase 4 | `get_content_tags`, `get_coverage_report` | `shuttersense://collections/{guid}/content` |
| Phase 5 | `get_cull_suggestions`, `get_group_ranking` | — |
| Phase 6 | — (enriches existing tools) | — |
| Phase 7 | `import_catalog_metadata`, `compare_ratings` | `shuttersense://catalogs/{guid}/summary` |

---

## Infrastructure Requirements

### Agent Changes

| Requirement | Phases | Notes |
|-------------|--------|-------|
| Pillow or pyexiv2 | 1, 3, 6 | Image reading and EXIF extraction |
| open-clip-torch | 2 | ~400MB model download, cached locally |
| torch (CPU) | 2, 3 | PyTorch for inference (CPU-only default) |
| mediapipe | 6 | Lightweight face detection (~30MB) |
| GPU support (optional) | 2, 3, 4 | Faster inference, not required |
| Cloud API client | 4 | Anthropic/OpenAI SDK for vision API calls |

### Server/Database Changes

| Requirement | Phases | Notes |
|-------------|--------|-------|
| pgvector extension | 2 | PostgreSQL vector similarity search |
| `image_embeddings` table | 2 | New table + HNSW index |
| Extended result JSONB schemas | 1, 3, 4, 5, 6 | New sections in existing result format |
| New tool type registrations | 3, 5 | `image_quality`, `smart_cull` |
| Catalog connector type | 7 | New connector subtype |

### Agent Binary Size Impact

| Component | Size Impact | Mitigation |
|-----------|------------|------------|
| Pillow | +5MB | Already common dependency |
| CLIP model weights | +400MB | Downloaded on first use, cached |
| PyTorch (CPU) | +150MB | Conditional install for AI features |
| MediaPipe | +30MB | Lightweight |

Consider an **agent feature flag** system: `shuttersense-agent --features=ai` to opt into AI capabilities, keeping the base agent binary lean for users who only need file-level analysis.

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Agent binary bloat from ML dependencies | Slower downloads, larger disk footprint | Feature flags, lazy model download, separate "AI agent" build |
| Cloud vision API costs at scale | Unexpected bills for large collections | Sampling strategies, cost estimation before run, local model fallback |
| CLIP model accuracy on specialized photography | Poor search results for niche content | Fine-tune on photography datasets, allow model selection |
| GPU requirement perception | Users think they need expensive hardware | CPU inference for all phases (slower but functional), clear documentation |
| Privacy concerns with face detection | User resistance, legal exposure | Detection-only (no recognition), team-level opt-out, no face embeddings stored |
| pgvector availability | Not all PostgreSQL hosts have it | Graceful degradation — disable search if unavailable, document requirement |
| Model version drift | Embeddings become incompatible across updates | Store model version with embeddings, re-embedding migration tooling |

---

## Success Metrics

| Metric | Target | Phase |
|--------|--------|-------|
| EXIF extraction coverage | >95% of common RAW/JPEG formats | 1 |
| Semantic search relevance (P@10) | >70% for common photography queries | 2 |
| Duplicate detection precision | >90% true duplicates in flagged set | 2 |
| IQA correlation with human ratings | >0.7 Spearman rank correlation | 3 |
| Content classification accuracy | >80% on standard scene categories | 4 |
| Cull suggestion acceptance rate | >60% of "reject" suggestions confirmed by user | 5 |
| Face detection recall | >95% for frontal/near-frontal faces | 6 |
| MCP query satisfaction | Users find answers via MCP for >80% of content questions | All |

---

## Non-Goals (This Roadmap)

- **Image editing/generation**: ShutterSense analyzes and manages photos, it does not edit them. Generative AI (inpainting, style transfer, AI upscaling) is out of scope.
- **Face recognition**: Identifying specific individuals requires consent workflows and legal review. Only anonymous face detection is in scope.
- **Real-time processing**: All AI analysis runs as batch jobs through the agent system. Live camera feed analysis is not planned.
- **Training custom models**: Using ShutterSense photo data to train or fine-tune models is out of scope. All models are used for inference only.
- **Replacing photographer judgment**: AI scores and suggestions are advisory. No automated deletion, rejection, or modification of photos.
