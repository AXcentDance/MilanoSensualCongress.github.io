# 2027 asset register

This is an index of existing assets, not a declaration that every file is
cleared for every channel. Existing website assets remain at their current
paths. Event copy must use the
[canonical edition record](../../data/editions/2027.json) and
[edition brief](edition-brief.md).

## Shared identity and 2027 visual

| Asset | Existing source or entry point | Current status and use |
| --- | --- | --- |
| Official logo master | [4096 × 4096 PNG](../../images/brand/milano-sensual-congress-official-logo-source.png) | Owner approved on 25 September 2026 for the website, presentations, videos, and future congress materials. Preserve the original artwork. |
| Logo handling and derivatives | [Official logo notes](../../images/brand/milano-sensual-congress-official-logo-notes.md), [build script](../../scripts/build_official_logo.py) | These sources own cropping, transparency, sizing, and reproduction details. Older rectangular and proposed colour-flex logos are historical references. |
| Large web logo | [WebP logo](../../images/milano-sensual-congress-official-logo.webp) | Existing website derivative; use the original master when preparing a new print layout. |
| 2027 navigation logo | [Small navigation WebP](../../images/milano-sensual-congress-official-logo-nav-2027.webp) | Optimised for the website header, not a print master. |
| Arrows-only browser favicon | [Current medium RGBA source](../../images/brand/milano-sensual-congress-tricolor-spires-favicon-medium-source.png), [32px PNG](../../images/milano-sensual-congress-tricolor-spires-favicon-medium-32.png), [192px PNG](../../images/milano-sensual-congress-tricolor-spires-favicon-medium-192.png), [16/32/48px ICO](../../favicon.ico), [recipe and provenance](../../images/brand/milano-sensual-congress-official-logo-notes.md#arrows-only-browser-favicon) | Owner requested thicker, more visible arrows after reviewing the live tab icon on 29 September 2026. The owner then requested a weight between the thin live icon and the bold preview. Current published revision uses medium stems and less outside padding; PNG and ICO exports preserve transparency. Seven tricolour spires with a shared lower baseline, no text. Built-in image generation adaptation of the approved logo. The medium revision was published on 29 September 2026 in commit `18a33eef`, replacing the thin transparent version from `6b43dd9a`. Earlier sources are preserved. Original logo approval covers website use; no new rights for unrelated channels are asserted. |
| Duomo and tricolour aircraft visual | [Main WebP](../../images/milano-2027-duomo-tricolore.webp), [480px derivative](../../images/milano-2027-duomo-tricolore_480w.webp) | Derived from the reference image supplied by the owner for the 2027 redesign. Current asset is 780 × 1076px; a higher-resolution master and broader campaign rights are not recorded here. |
| Design system | [Brand rules](../../.agent/rules/brand-coherence.md), [2027 scene palette](../../css/edition-personality.css), [font setup](../../css/fonts.css) | Canonical visual direction; applies across website and promotional materials. |

### Visual identities by subject

Use these website references when preparing a related promotional piece. Keep
the shared palette and official logo, while choosing the composition that fits
the subject rather than repeating one layout for everything.

| Subject | Visual reference | Style source |
| --- | --- | --- |
| Main edition announcement | Cinematic Duomo-to-sky film, emerald, ivory, Italian red and architectural gold | [Homepage identity](../../css/home-premiere.css) |
| Artists, workshops, parties, competition | Portrait stage, itinerary, cobalt night, citrine studio, amber arena | [Experience scenes](../../css/edition-stage.css) |
| Hotel, booking, passes, travel, contact | Architectural warmth, concierge, ticket stubs, arrival diagram, conversation | [Visit scenes](../../css/edition-stay.css) |
| Journal, Ambassadors, guides and archive | Colour magazine, Italian tricolour invitation, topic-specific article treatments | [Editorial scenes](../../css/edition-culture.css) |

## Website motion and media

This branch contains the website draft and its rebuild dependencies. Separate
merchandise proofs, print exports, native video takes and unrelated creative
drafts remain outside this release; their owner workspace copies are preserved.

| Asset | Entry point | Scope and status |
| --- | --- | --- |
| Official wordmark Duomo film v07 | [Source record and web encoder](sources/frecce-tricolori-duomo/README.md#official-wordmark-v07--without-the-year) | Owner-selected homepage film, without a baked-in year. Short finished masters and bounded web derivatives accompany this branch. Earlier generated source takes are excluded. |
| Klau y Ros hover preview | [Excerpt provenance and rebuild recipe](sources/klau-ros-insomnia-mexico/README.md) | Owner-requested 20-second website excerpt; all five HLS fragments and initialization file accompany the playlist. Full-length original remains outside Git. |
| Community map | [Map source notes](../../images/europe-community-atlas-notes.md), [flag provenance](../../images/flags/README.md) | Website community illustration and country flags. |
| Hotel and artist photography | Existing files under `images/hotel/` and `images/artists/` | Preserved website media. Their presence does not establish 2027 artist bookings, hotel availability, or permission for unrelated print uses. |

Event facts remain owned by the edition record. This branch release does not
publish the 2027 edition to the live 2026 website or approve unrelated campaigns.
