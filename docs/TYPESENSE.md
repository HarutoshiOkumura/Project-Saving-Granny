# Typesense (prize: "Best Use of Search with Typesense")

**Prize text:** "Most creative/ingenuitive way of using search with correct implementation that leverages Typesense in full capacity." Judged on creativity, implementation and usefulness. The winning team gets $1,500 of Typesense Cloud credit.

**The Typesense judging sheet lists:**
1. innovation and creativity
2. technical difficulty and implementation ("use a niche search…")
3. practical impact
4. design and UX (accessibility)
5. pitch

→ **Name matching alone won't win. Use several niche features, visibly.**

Checked against the Typesense 30.2 docs and the `typesense` Python client 2.1.1 source on 14 Nov.

## Run it
- Self-host 30.2, either way:
  - Docker `typesense/typesense:30.2`;
  - the binary at `https://dl.typesense.org/releases/30.2/typesense-server-30.2-linux-amd64.tar.gz`, run as `./typesense-server --data-dir=DIR --api-key=KEY --enable-cors`.
  - Port 8108 (`--api-port`).
- Built-in embedding models need about 2–6 GB RAM. The Typesense Cloud free tier (0.5 GB) is too small for them.
- Analytics flags:
  - `--enable-search-analytics=true`
  - `--analytics-dir=DIR`
  - `--analytics-flush-interval=60` (the self-hosted default is 3600)
  - `--analytics-minute-rate-limit=600` (the default is 5)
- Python: `pip install typesense==2.1.1`.

  | Area | Calls |
  |---|---|
  | collections | `client.collections.create/retrieve` |
  | documents | `client.collections[c].documents.create(doc)`, `.import_(docs, {"action": "upsert"})`, `.delete({"filter_by": …})`, `.export()`, and `documents[id].update(partial)` |
  | search | `client.multi_search.perform(searches, common_params)` |
  | synonyms | `client.synonym_sets[name].upsert(body)` |
  | stopwords | `client.stopwords.upsert(set_id, body)` |
  | analytics | `client.analytics.rules.create(rule)` / `.retrieve()` |
  | NL models | `client.nl_search_models.create(m)` / `[id].update(m)` |
  | RAG models | `client.conversations_models.create(m)` / `[id].update(m)` |
  | keys | `client.keys.create(spec)`, `client.keys.generate_scoped_search_key(parent_value, params)` (returns bytes) |

  Errors: `typesense.exceptions.ObjectAlreadyExists` (409), `ObjectNotFound`, `RequestUnauthorized`.
- v30 removed `/collections/{c}/synonyms`. Use `/synonym_sets`.

## Role in this repo (D28 default)

**Postgres stays the source of truth.** `scripts/sync_typesense.py` runs after the seed and after each dashboard edit, and copies:
- items: name, aliases, description, category
- places: landmark and room spoken names
- facts (D29)
- optionally, sightings for the dashboard timeline

**Voice:** Typesense turns the spoken phrase into an item name, then `rank_item(name)`. `find_item` and `rank_item` match only exact names or aliases. Typesense adds:
- typo tolerance ("spectecles")
- synonyms ("specs", "clicker")
- meaning ("the thing I read with")

## Features and exact syntax

1. **Per-person synonym sets.** `PUT /synonym_sets/{name}`:
   ```json
   {"items": [{"id": "specs", "root": "specs", "synonyms": ["glasses"]},
              {"id": "tv", "synonyms": ["tv", "television"]}]}
   ```
   - One-way (has `root`): searching the root also finds its synonyms, not the reverse.
   - Multi-way (no `root`): any member finds any other.
   - Apply per search: `"synonym_sets": "grandma-objects,common"`.
   - Synonyms apply only to `q`, never to `filter_by`.
   - `"synonym_num_typos": 1` lets "clikcer" still map.
2. **Spoken input.** Search settings:
   - `num_typos` 2, `min_len_1typo` 4, `min_len_2typo` 7
   - `typo_tokens_threshold` 1, `drop_tokens_threshold` 1
   - `split_join_tokens` `"fallback"` (the default)
   - `prefix` false (speech has no partial words)
   - `prioritize_exact_match` true

   Stopwords: `client.stopwords.upsert("spoken", {"stopwords": ["where", "is", "are", "my", "the", "did", "i", "put", "find", "lost", "please"], "locale": "en"})`, then `"stopwords": "spoken"` per search. Never list a word that is part of an item or place name.
3. **Hybrid search (keywords plus meaning).** Add an auto-embedding field and put it in `query_by`:
   ```json
   {"name": "embedding", "type": "float[]",
    "embed": {"from": ["name", "aliases", "description"],
              "model_config": {"model_name": "ts/all-MiniLM-L12-v2"}}}
   ```
   - Fusion: `rank_fusion_score = (1 − alpha)·K + alpha·S`, where K is the keyword rank, S the semantic rank, and `alpha` the vector weight (default 0.3).
   - Per query: `"vector_query": "embedding:([], alpha: 0.3, distance_threshold: 0.55)"`.
   - `"rerank_hybrid_matches": true` gives every hit both `text_match_info` and `vector_distance`. Use them to classify the match: exact, synonym, meaning or ambiguous.
   - Tune 0.55 on 20–40 labelled phrases.
4. **Analytics on searches that found nothing (the key trick).**
   - Vector search treats every document as a match at some distance, so a hybrid query never returns zero hits. `nohits_queries` therefore never fires **unless `distance_threshold` is set**.
   - With it, "dentures" (not enrolled) returns `found: 0`. The agent says "I don't know that one yet", and the query is logged for the dashboard's "Grandma asked, we couldn't answer → Enroll" list.
   - Rules (v30 format):
     ```json
     {"name": "items_popular", "type": "popular_queries", "collection": "items", "event_type": "search",
      "params": {"destination_collection": "q_popular", "limit": 500, "capture_search_requests": true}}
     ```
     ```json
     {"name": "items_nohits", "type": "nohits_queries", "collection": "items", "event_type": "search",
      "params": {"destination_collection": "q_nohits", "limit": 500}}
     ```
   - Destination schema: `{"name": "q_nohits", "fields": [{"name": "q", "type": "string"}, {"name": "count", "type": "int32"}]}`.
   - Pass `"enable_analytics": false` on internal and dashboard searches.
   - If `q_nohits` stays empty after a flush, add `"capture_search_requests": true` to the no-hits rule, verify, and note it in `STATUS.md`.
5. **Scoped search keys.**
   - Parent key: `client.keys.create({"description": "…", "actions": ["documents:search"], "collections": ["items", "places", "facts"]})`. Its `value` is shown once, and it must have **only** `documents:search`.
   - Per user: `client.keys.generate_scoped_search_key(parent, {"filter_by": "home_id:=…", "expires_at": <epoch seconds>, "exclude_fields": "embedding"})`.
   - Embedded parameters cannot be overridden.
   - **Caveat:** a key scoped to a collection also exposes the collections its schema references, via joins.
   - Uses: the dashboard search box in the browser (D16 forbids a Supabase key there; Typesense scoped keys are designed for browsers), and keeping caregiver-only facts away from the patient's agent (embedded `visibility:=patient`).
6. **Union search.** `POST /multi_search?page=1&per_page=12` with `{"union": true, "searches": [...]}` merges items, places, facts and timeline into one ranked list.
   - Per-search `page`/`per_page` are ignored.
   - Every search must sort the same way; use `"sort_by": "_text_match:desc"` in each.
   - Duplicates are removed by default; `"remove_duplicates": false` keeps them.
   - Hits carry no collection marker, so put a `kind` field in every document.
7. **JOINs.**
   - Declare `{"name": "item_id", "type": "string", "reference": "items.id"}`. Add `"optional": true, "async_reference": true` if the referenced document may arrive later.
   - `"include_fields": "$items(name,aliases)"` returns the joined document nested under `document["items"]`.
8. **Natural-language search** (the family types "where were the keys yesterday afternoon").
   - Create the model with `POST /nl_search_models`: `{"id": "nl", "model_name": "google/gemini-2.5-flash", "api_key": "…", "max_bytes": 16000, "temperature": 0.0, "system_prompt": "…"}`. The docs example uses `google/gemini-2.5-flash`; `google/gemini-3.5-flash` should work but is *unverified*.
   - Search with `"nl_query": true, "nl_model_id": "nl"`. Your own `filter_by` is ANDed with the generated one.
   - Show `parsed_nl_query.generated_params` as "Save It understood: …".
   - Put today's date in the system prompt; refresh it with `client.nl_search_models["nl"].update(...)`.
9. **Conversational RAG over family facts** ("Who is June?", "What tea does Mom like?").
   - History collection (exact schema required):
     ```json
     {"name": "conversation_store", "fields": [
       {"name": "conversation_id", "type": "string"}, {"name": "model_id", "type": "string"},
       {"name": "timestamp", "type": "int32"},
       {"name": "role", "type": "string", "index": false}, {"name": "message", "type": "string", "index": false}]}
     ```
   - Create the model with `POST /conversations/models`: `{"id": "rag", "model_name": "google/…", "history_collection": "conversation_store", "api_key": "…", "system_prompt": "…", "max_bytes": 16384, "ttl": 86400}`. The docs example uses `google/gemini-2.0-flash`.
   - Query:
     ```python
     client.multi_search.perform(
         {"searches": [{"collection": "facts", "query_by": "embedding", "exclude_fields": "embedding"}]},
         {"q": question, "conversation": True, "conversation_model_id": "rag"},
     )
     ```
     - Read the answer from `resp["conversation"]["answer"]`.
     - Pass `resp["conversation"]["conversation_id"]` back for follow-ups.
     - `"conversation_stream": true` streams the answer.
   - `query_by` must be an auto-embedding field. **`exclude_fields` controls what reaches the LLM:** exclude raw names and send pseudonymised text (`docs/DASHBOARD.md`, Privacy).
10. **Image search (CLIP).**
    - Fields: `{"name": "photo", "type": "image", "store": false}` plus `{"name": "photo_embedding", "type": "float[]", "embed": {"from": ["photo"], "model_config": {"model_name": "ts/clip-vit-b-p32"}}}` (512-d).
    - Text→image: `q` + `query_by: photo_embedding`.
    - Image→image: `"vector_query": "photo_embedding:([], image:<base64>, k:10)"`.
    - Use: the family uploads a photo of the lost thing and gets matching crops.
    - For an optional embedding field, send `[]` to skip generation.
11. **Geo (optional).** A `geopoint` field holds `[lat, lng]`. Filter with `location:(lat, lng, 0.006 km)`, sort with `location(lat, lng):asc`; each hit carries `geo_distance_meters`.
12. **Filter literals.** Wrap string values that contain special characters in backticks, e.g. ``name:=`Sam, the Dragon` ``.

## Demo story for the Typesense judges
- **One spoken question** shows off synonyms, typo tolerance, hybrid meaning and no-hit analytics.
- **The dashboard** shows:
  - union search
  - NL search with the parsed filter
  - RAG over family facts
  - scoped keys (patient vs family)
  - the "couldn't answer" list
