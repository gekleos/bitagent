# Sonarr integration

BitAgent exposes a standards-compliant Torznab endpoint that Sonarr can consume directly as a Custom Indexer.

## Setup

1. **Open Sonarr → Settings → Indexers → Add → Torznab → Custom**.
2. Fill in the connection fields:

   | Field | Value |
   |---|---|
   | Name | `BitAgent` |
   | Enable | ✓ |
   | URL | `http://bitagent:3333/torznab` (compose service name) or `https://bitagent.example.com/torznab` (public host) |
   | API Key | your `TORZNAB_API_KEY` |
   | Categories | `5000` (TV), `5030` (TV/SD), `5040` (TV/HD) — pick what your library tracks |
   | Anime Categories | leave blank unless you specifically curate anime |
   | Priority | `25` (high) to `50` (medium-fallback) — tune per your stack |
   | Download Client | leave blank to use Sonarr's default |
   | Tags | optional |

3. Click **Test**. The button turns green: *"Test was successful"*.
4. Save.

`[screenshot: sonarr-add-indexer-form]`

## What you should see

After save, Sonarr immediately runs a series RSS sync. Within 1–2 minutes the **System → Status** page shows BitAgent as a registered indexer with a recent successful query.

The first full search (manually triggered on a monitored episode) returns results within ~3–5s under typical DHT load. Results include:

- **Title** — the parsed release name as discovered by BitAgent's classifier
- **Size** — derived from BEP-9 metainfo
- **Seeders / Peers** — current DHT swarm health
- **Quality** — Sonarr's parser maps from the title
- **Indexer** — `BitAgent`

`[screenshot: sonarr-search-results]`

## Categories reference

| Newznab ID | Sonarr label | Notes |
|---|---|---|
| 5000 | TV | catch-all |
| 5030 | TV/SD | < 720p |
| 5040 | TV/HD | 720p+ |
| 5045 | TV/UHD | 2160p+ (if your BitAgent classifier emits it) |
| 5070 | TV/Anime | anime-specific |

`[screenshot: sonarr-categories-selector]`

## Troubleshooting

**Test returns "Connection failed"**
The most common cause is using `localhost` from inside Sonarr's container, where it resolves to the Sonarr container itself, not BitAgent. Use the **compose service name** (`bitagent`) or the **public host** (`bitagent.example.com`). Both are reachable from the Sonarr container.

**Test returns 401**
Check that the API Key field matches `TORZNAB_API_KEY` exactly. Whitespace and quotes are easy to fat-finger when copying from a `.env` file.

**Search returns 0 results**
Confirm that BitAgent has discovered torrents. In the BitAgent dashboard, the Library tab should show recent entries. If empty, check the DHT bootstrap configuration in your deployment.

`[screenshot: sonarr-test-failed-401]`

## Recommended companions

- **Custom Formats** — once BitAgent's evidence-pipeline confidence scores stabilise, you can layer Sonarr Custom Formats on top to prefer high-confidence releases.
- **Quality Profiles** — leave standard; BitAgent's classifier already tags resolution + source, so Sonarr's parser handles the rest.
- **Indexer flags** — flag BitAgent as a "freeleech-friendly" custom indexer if you only run it locally.

For multi-instance Sonarr setups, repeat the setup in each instance — BitAgent does not require any special multi-tenant configuration.
