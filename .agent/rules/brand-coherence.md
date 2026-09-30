---
trigger: always_on
---

# One brand, distinct page identities

Every page belongs to Milano Sensual Congress, but the owner explicitly asked
on 26 September 2026 for a distinct personality on every page. Keep the official
logo, navigation, fonts, factual standards and accessibility consistent. Give
page families different compositions, colours, imagery, light and motion; do
not repeat a monochrome horizontal-section template. English and Italian
counterparts share their respective page identity.

## Source of truth

Before designing or creating a page, inspect `index.html`, `it/index.html`,
`tailwind.config.js`, and `css/fonts.css`. Reuse the current homepage's visual
patterns and shared assets. A subpage with a different aesthetic is not a brand
reference. If the user changes the homepage's brand direction, follow that
updated direction on subsequent new pages.

## Required visual language

- **Official logo (owner approved 25 September 2026):** Use the supplied
  tricolor spires and pink/purple Milano Sensual Congress wordmark for the
  website, presentations, videos, and future congress materials. The rectangular
  logo is retired. The exact supplied source is
  `images/brand/milano-sensual-congress-official-logo-source.png`; web copies use
  the `milano-sensual-congress-official-` filenames. Rebuild size variants with
  `python3 scripts/build_official_logo.py`. Preserve the artwork, lettering,
  colors, and proportions. The older rectangular assets and color-flex SVG
  concepts are historical references, not current brand assets. See the
  [official logo notes](../../images/brand/milano-sensual-congress-official-logo-notes.md).

- **Browser favicon (owner requested 28 September 2026):** Use only the seven
  tricolour spires, with their pyramid tops and lower stems extended to a
  symmetrical common baseline. On 29 September the owner requested a transparent
  background; preserve alpha in the PNG and ICO exports. The owner subsequently
  found the tab icon too thin, then requested a weight between the original
  and the bold preview. Use the medium spires with less outside padding, and
  inspect the native 16px export as well as higher-resolution variants.
  This dedicated favicon is separate from the unchanged full official logo.
  Its source and export recipe are in
  the [official logo notes](../../images/brand/milano-sensual-congress-official-logo-notes.md#arrows-only-browser-favicon).

- **Homepage direction (owner refined 27 September 2026):** The owner rejected
  the playful “Milano, In Full Colour” presentation and requested a serious
  homepage inspired by `https://feverbachataworldmeeting.com/`. The current
  homepage opens with the Duomo-to-sky title film, fading into its
  emerald background, and uses large centered headlines and straight artist
  cards with muted hover previews. On phones, small play/stop buttons beside
  artist names control those previews; activating them must preserve the user's
  scroll position (owner clarification, 29 September 2026). The opening headline fades away when the
  film title finishes appearing. The camera opening plays once, then a seamless atmospheric loop keeps the
  tricolour smoke and sky gently moving behind fixed lettering, with the Duomo
  outline visible below. The owner selected the v06 film on 27 September 2026:
  its ending uses the exact official pink/purple and white script wordmark.
  On 28 September the owner requested a v07 rebuild without the separate gold
  year beneath that wordmark. Earlier video versions remain preserved.
  The owner requested no film or floating motion buttons
  on the homepage. Its
  original emerald, ivory and Italian red palette, with restrained architectural
  gold, is defined in `css/home-premiere.css`. Preserve the official logo.
  This request explicitly covers **the homepage only**, in both languages;
  do not propagate it to other pages without an owner request.
- **Homepage early-bird signup (owner refined 27 September 2026):** Use large,
  centered cream display lettering and gold italic emphasis against the emerald
  page, with soft green/red light, a clearly fillable ivory email input and a solid
  red reminder button, taking inspiration from the live homepage form. The owner
  rejected the ivory rectangular panel as too corporate. Keep this invitation
  centered directly beneath the film’s congress title, with the early-bird
  countdown and reminder form together. The owner subsequently requested clearer
  separation from the film: use an opaque deep-emerald surface, a restrained gold
  edge, stronger typography and a prominent countdown. Keep the input ivory and
  the action red; do not restore the earlier ivory corporate panel. The confirmed event
  dates now appear prominently above the offer, between the film title and signup,
  as requested by the owner. On 28 September the owner requested a different
  reminder action: use the flat red capsule with an outlined bell, replacing
  the sculpted button and ivory arrow disc. The venue line reads “4-star
  Superior · Devero Hotel” in larger type (translated in Italian). The owner
  further requested a larger, more readable date/month/venue block: keep clear
  ivory dates and a pale-gold venue line with strong contrast over the film.
  On 28 September the owner refined the film framing: make it slightly smaller
  on desktop, centered with soft fading margins on the left and right. Use a
  restrained inset above 1000 px and retain the full viewport width on phone
  and tablet. Preserve the complete source frame at its natural 16:9 ratio;
  the signup can continue into the matching emerald background on small screens.
- **Homepage ending (owner refined 28 September 2026):** Keep the Ambassador
  invitation compact and use the full event name in “Represent Milano Sensual
  Congress around the world”. The separate 2026 booking/countdown section has
  been removed from both homepages; other explicitly labelled 2026 reference
  content and archive links remain. On 29 September the owner also removed
  the homepage experience (`#the-congress`) and journal (`#home-journal`)
  sections in both languages. Do not restore these sections or include them
  in the homepage chapter navigation; their standalone pages remain available.
- **Homepage community map (owner selected 28 September 2026):** Use the
  sculpted emerald Europe treatment: richer green land, shallow relief, fine
  gold coastlines and a fixed red Milano destination. Selecting a country
  smoothly moves the route origin to its representative capital and reshapes
  the curve; reduced motion switches immediately. Keep the 2026 community
  context in the section introduction. The owner subsequently requested
  “Artists representing the country” for the artist statistic and removal of
  the edition/demo footer beneath the selected country's figures. The data
  remains a local layout demo, not confirmed attendance statistics. The shared SVG is
  `images/europe-community-sculpted-emerald-coastlines.svg`.
  The owner subsequently requested all flags in a compact panel beside the map.
  The latest refinement keeps the picker visible after selection, with the
  selected country's compact statistics above it in the same column. Show four
  flag rows at a time and allow scrolling/search to reach the remaining flags.
  Keep the map and panel steady between selections. On 29 September the owner
  requested thin country borders on the phone map only. Its base asset is
  `images/europe-community-sculpted-emerald-country-borders.svg`; desktop and
  tablet retain the coastlines variant. The existing
  [atlas notes](../../images/europe-community-atlas-notes.md) own its geographic
  source and rebuild details.
- **Homepage artist cards and journey planning (owner refined 28 September
  2026):** Remove the decorative number badges from every artist card. Give
  journey planning the full lower subsection of the venue invitation, with a
  prominent “Plan your journey with us” action (translated in Italian), linking
  to the corresponding transfer page. On 29 September the owner requested a
  schematic Malpensa (MXP) → Devero Hotel shuttle panel with departures at
  15:00, 18:00 and 20:00, showing MXP only. Read the scoped route confirmation
  in the edition record; do not add a departure day, return service or booking
  terms that the owner has not supplied.
- **Homepage learning invitation (owner requested 28 September 2026):** Place
  the inclusive workshop section after the artists and before the hotel. Show
  three workshop rooms and clearly named beginner, intermediate and advanced
  levels with green, yellow and orange visual cues. Give masterclasses a
  distinct invitation. Describe suitable options in every workshop slot as
  the organizing team's programming priority while the timetable remains
  unannounced. Use the confirmed workshop facts in the 2027 edition record;
  do not imply fixed room-to-level assignments or pass inclusions. The owner
  subsequently requested more personality and a timetable treatment: use an
  ivory paper board with three room columns and green/yellow/orange workshop
  blocks, rotating levels across illustrative slots. The table's accessible
  label identifies it as an example and says the final schedule is forthcoming;
  the owner removed the visible example note on 29 September. The owner selected
  19:00, 20:00, 21:00 and 22:00 as example row labels, not confirmed programme times,
  and removed the opening “Whatever your starting point, you belong here.”
  sentence (and its Italian equivalent). The owner also removed the large
  background “03” and requested Bachata Sensual, Bachazouk, Esencia Style and
  Bachata Dominicana in this section. Show the styles within the illustrative
  timetable blocks alongside the coloured levels; their example placements
  are not confirmed room or time assignments. Keep masterclasses in a
  separate invitation, without implying ticket or pass inclusions.
  On 29 September the owner clarified that offering three styles and three
  levels every hour is a programming aim and effort, not a guarantee.
  The owner also requested a more compact vertical layout and a red
  **Masterclass** block at the illustrative 22:00 row. That block spans the
  three room columns, with no parallel workshop cells in that example row.
  Its time and placement remain illustrative; the final timetable and actual
  room assignments are unannounced. The owner then changed the separate
  invitation to **Masterclass tickets**, featuring **Gero y Migle, Klau y Ros
  and Pablo y Raquel**, with **Take your ticket** / **Prendi il tuo biglietto**.
  This ticket action uses the concert-ticket styling and links to the local
  `/tickets` or `/it/tickets` information page. Do not substitute a 2026
  checkout or upgrade anchor, or imply new ticket availability or prices.
- **Existing subpage direction:** The remaining pages still use the earlier
  expressive palette and compositions in `css/edition-personality.css`:
  midnight ink, warm ivory, cobalt, lilac, coral, citrine, petrol and amber.
  Their unchanged treatment is not approval to restore that look on the home.
- **Page personalities:** Artists is an indigo portrait stage; Programme a
  connected itinerary; Parties a cobalt night scene; Masterclass a citrine
  studio; Jack & Jill an amber arena. Hotel is warm architectural hospitality,
  booking a peach concierge, Tickets cobalt/citrine stubs, Transfer a mint
  route map, Contact coral/lilac conversation, Journal a colour-rich magazine.
  Ambassador retains the Italian tricolour invitation. FAQ, Terms, the archive
  and article topics have their own restrained but recognisable treatments.
- **Artists title (owner requested 29 September 2026):** Use an oversized
  “Artists” / “Artisti” opening, inspired by the fast typographic reveal at
  DevDay. Seven decorative tricolour stars and stems sit behind the lettering;
  these are separate from the unchanged official logo. Letters briefly draw
  as outlines and settle into solid ivory in under a second. Keep the static
  heading readable without JavaScript and with reduced motion, and respect
  the shared motion pause control. Portrait links remain below the title.
- **Energy and directness:** Use short, direct copy, oversized typography,
  image-led openings and expressive motion. Preserve useful article content
  and practical booking information. Light accents are now explicitly requested;
  use them purposefully without washing out text or creating noisy generic cards.
- **Typography:** Use self-hosted Inter with heavy display weights for major
  headlines, and Playfair Display for selective italic accents. Body copy,
  navigation and controls use Inter, with Playfair Display italic reserved for
  the owner-requested homepage ticket CTA labels. Do not introduce a different
  font pairing.
- **Navigation and footer:** Carry over the homepage's logo treatment, sticky
  navigation, mobile menu, language switcher, and footer styling. Adapt link
  paths and active states to the page and language; follow the
  [breadcrumb contract](breadcrumbs.md).
- **Buttons and controls:** The owner refined the homepage buttons on
  28 September 2026, rejecting circular arrow badges and asking for a more
  artistic treatment. On 29 September the owner limited the concert-ticket
  treatment to ticket/pass booking actions: warm paper, perforation details and
  restrained red accents, with no arrow discs. Programme, hotel, masterclass
  information and Ambassador navigation must not look like purchase tickets. Use underlined
  editorial links or the existing standard buttons. Keep the separately
  approved red bell reminder action. Other pages retain their existing
  palette-based buttons. Preserve generous touch targets, accessible labels
  and clearly visible keyboard focus states.
- **Layout and surfaces:** Match the homepage's container widths, spacing
  rhythm and legibility, while varying composition, silhouette, surfaces and
  interactions by page. Use offset portraits, architectural crops, stage lighting
  and purposeful connectors instead of repeating ruled horizontal rows.
- **Imagery and motion:** Follow `css/edition-motion.css` and
  `js/edition-motion.js` and the scene stylesheets: moving spotlights, artwork
  movement, expressive image hovers, chapter navigation and scroll entrances.
  Keep content visible before enhancement.
  Subpages provide a pause control for ongoing motion. The homepage uses
  `js/home-motion.js` without a floating control, as requested by the owner.
  Respect reduced-motion/data-saving preferences and preserve the project's
  performance requirements.
- **Ambassadors:** `/promoters` and `/it/promoters` use a concise invitation,
  one application action and an oversized Italian tricolour “Ambassador” word.
  Keep it readable as one word and maintain contrast on the dark background.

## Preview facts

The 2027 branch is a local edition preview. The organizer confirmed Devero Hotel
and 19–21 November 2027 on 26 September 2026. The canonical confirmed-fact record
is [`data/editions/2027.json`](../../data/editions/2027.json); the
[materials brief](../../materials/2027/edition-brief.md) routes website, flyer
and promotional work to that record and the existing asset sources.
Exact event times, prices, booking availability and the final 2027 lineup have
not been confirmed. Current artists and video remain preview references by
request. Keep exact 2026 operational information visibly labelled as such; do
not redate archive articles or label the existing 2026 checkout as a 2027 sale.

## Precedence and verification

A separate visual identity requires an explicit user instruction; use the
precedence in [AGENTS.md](../../AGENTS.md#precedence-and-scope).

Before considering a new page complete, compare it visually with the homepage
at mobile, tablet, and desktop widths (375, 768, and 1440px), and check equivalent
styling in both languages. Fix unintended language mismatches and usability differences; purposeful
palette and composition differences between page families are required. Complete the shared
[delivery checks](delivery.md#verification-and-completion); automated checks do
not replace this visual comparison.
