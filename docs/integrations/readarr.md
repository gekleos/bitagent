# Readarr integration

Readarr is the ebook + audiobook member of the `*arr` family. BitAgent answers both Readarr's book and audiobook search calls — books map to the Newznab 7000-series categories, audiobooks to category `3030`. A single BitAgent indexer entry per Readarr instance is sufficient.

## Setup

1. **Open Readarr → Settings → Indexers → Add → Torznab → Custom**.
2. Fill in the connection fields:

   | Field | Value |
   |---|---|
   | Name | `BitAgent` |
   | Enable | ✓ |
   | URL | `http://bitagent:3333/torznab/api` (compose service name) or `https://bitagent.example.com/torznab/api` (public host) |
   | API Key | your `TORZNAB_API_KEY` |
   | Categories | `7020` Comics, `7030` Magazines, `7040` Technical/eBook, `7050` Other, `7060` Foreign — pick what your library tracks |
   | Early Download Limit | leave default |
   | Priority | `25` (high) to `50` (medium-fallback) — tune per your stack |
   | Tags | optional |

3. Click **Test**. The button turns green: *"Test was successful"*.
4. Save.

For a separate Readarr **audiobook** instance, repeat the setup with category `3030` selected instead.

## Search modes

Readarr issues two distinct Torznab functions depending on which media class is monitored:

- `t=book` — for ebooks. Sends `author`, `title`, sometimes `q`. BitAgent maps to 7000-series.
- `t=audio` — for audiobooks. Sends `artist`, `album`. BitAgent maps to category `3030`.

Both functions are answered by the same BitAgent endpoint; the routing is per-request, not per-indexer-entry.

## Categories reference

| Newznab ID | Readarr label | Notes |
|---|---|---|
| 3030 | Audio / Audiobook | use for audiobook instances |
| 7000 | Books | catch-all |
| 7020 | Books / Comics | comics + manga |
| 7030 | Books / Magazines | periodicals |
| 7040 | Books / Technical | non-fiction, eBook releases |
| 7050 | Books / Other | misc |
| 7060 | Books / Foreign | non-English |

If your Readarr instance only tracks audiobooks, leave the 7000-series boxes unchecked and pick `3030` only — this keeps Readarr's indexer cache lean.

## Troubleshooting

**Test returns "Connection failed"**
The URL field is referencing `localhost`, which from inside Readarr's container resolves to Readarr itself, not BitAgent. Use the **compose service name** (`bitagent`) or the **public host** — both are reachable from Readarr's network.

**Test returns 401**
The API Key field does not match `TORZNAB_API_KEY`. Common causes: trailing whitespace pasted from a `.env` file, surrounding quotes, a stale value left over from a previous BitAgent install.

**Search returns 0 results**
Confirm BitAgent has discovered torrents at all — open the BitAgent dashboard's Library tab. If empty, the DHT bootstrap is the problem (see [troubleshooting.md](../troubleshooting.md)). If the dashboard shows torrents but Readarr's search misses, try the same `author`+`title` query manually via curl against `/torznab/api?t=book`. If curl returns results and Readarr does not, the issue is most likely a Readarr category-map mismatch.

**Audiobook search returns ebooks (or vice versa)**
The category map on the BitAgent indexer entry is wrong for the Readarr instance type. For an ebook instance, only 7000-series categories should be selected. For an audiobook instance, only `3030`. Mixed selections cause Readarr to ingest results from the wrong media class.

## Recommended companions

- **Custom Formats** — once BitAgent's evidence-pipeline confidence stabilises (typically after 1–2 weeks of `*arr` grab feedback), layer Readarr Custom Formats to prefer high-confidence releases.
- **Quality Profiles** — leave standard; BitAgent's classifier already tags audio format / bitrate / source, so Readarr's parser handles the rest.
- **Indexer flags** — flag BitAgent as a fallback indexer for hard-to-find titles. Private trackers handle the headline catalog; BitAgent extends reach into older or less-popular titles that aren't on private indexers.

For multi-instance Readarr setups (typical: one ebook instance + one audiobook instance), repeat the setup in each — BitAgent does not require any special multi-tenant configuration.

## See also

- [Torznab API reference](../reference/torznab-api.md)
- [Sonarr integration](sonarr.md) — the same patterns apply for TV
- [Lidarr integration](lidarr.md) — sister `*arr` for music
- [Configuration](../configuration.md) — `TORZNAB_API_KEY` setup
