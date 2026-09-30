# Milano Sensual Congress materials

This catalog brings together the event information and creative assets used by
the website, flyers, social posts, videos, and presentations. Existing assets
stay at their current paths so website links and build recipes keep working.

## Start here

| Need | Source |
| --- | --- |
| Confirmed 2027 event facts | [2027 edition record](../data/editions/2027.json) — canonical fact record |
| Ready-to-use English and Italian event copy | [2027 edition brief](2027/edition-brief.md) — a working summary of the record |
| Existing artwork, photographs, film, and artist clips | [2027 asset register](2027/asset-register.md) |
| Visual identity and official logo policy | [Brand rules](../.agent/rules/brand-coherence.md) |
| Publication and verification workflow | [Delivery rules](../.agent/rules/delivery.md) |

When a fact changes, update the edition record from the owner's confirmation,
then revise the brief, website, and affected promotional exports together.
Never infer a new edition's prices, artist bookings, programme, or commercial
terms from an earlier edition.

The 2027 record also holds the confirmed early-bird final day, 30 December 2026.
Use the edition brief for its countdown interpretation; pass prices and the
2027 checkout still await confirmation.

It also records the three workshop rooms, beginner/intermediate/advanced
levels, Bachata Sensual, Bachazouk, Esencia Style and Bachata Dominicana,
and planned masterclasses. On 29 September 2026, the owner clarified that
offering three different styles and three different levels each hour is a
planning aim, not guaranteed hourly coverage. The three workshop rooms remain
confirmed. The edition brief provides
English and Italian copy under **A congress for every style and level /
Un congresso per ogni stile e livello**, and distinguishes the programming aim
from unannounced timetables, room assignments and booking terms.

On 29 September 2026, the owner selected Gero y Migle, Klau y Ros and Pablo y
Raquel for the homepage masterclass ticket invitation, without confirming the
complete lineup or ticket availability, prices or checkout. The record also
holds the Malpensa Airport (MXP) shuttle departures at 15:00, 18:00 and 20:00.
On 30 September 2026, the owner confirmed that it serves Devero Hotel or
AS Hotel Cambiago. Both destinations are served, without a confirmed stop order;
its departure day, return service and commercial terms remain unannounced.
See the edition brief for matching English and Italian copy.

On 30 September 2026, the owner also confirmed **BGY / LIN → Hotels** transfers
from Bergamo Orio al Serio and Milan Linate to either hotel, with advance booking
via [WhatsApp at +39 366 207 3769](https://wa.me/393662073769). The separate
**BGY / LIN → Hotel** invitation in Italian carries the same routes and booking
requirement. These transfers do not inherit the MXP departure times or the live
transfer page's explicitly 2026 fares and service availability. The edition brief
provides the matching bilingual copy and preserves the unannounced 2027 details.

## Filing new work

Keep new creative work under its edition. Use the following structure when
the first corresponding file is created; the folders below are a filing plan,
not an inventory of files already delivered.

```text
materials/
  README.md
  2027/
    edition-brief.md
    asset-register.md
    sources/          # Public-safe editable artwork, organised by campaign
    exports/
      print/          # Final printer-ready files and matching proofs
      social/         # Final posts, stories, and platform-specific exports
      video/          # Final promotional edits and caption files
      presentations/  # Final slide decks and PDFs
```

For example, use
`msc-2027-save-the-date-en-instagram-1080x1350-v01.png` or
`msc-2027-save-the-date-it-a5-print-v01.pdf`. Include the edition, purpose,
language, format or size, and revision. Keep the editable source linked to its
exports in the asset register. Do not overwrite a released export with different
content under the same revision.

For each new item, record its path, purpose, language, dimensions or print
specification, source/creator, rights information available, content status,
approval status, and the source revision used. Use explicit statuses such as
**draft**, **reviewed**, **owner approved**, and **released** only when supported
by an actual review, approval, or release. Approval to reuse a logo is separate
from approval of the copy in a flyer.

## Edition boundaries and privacy

- Preserve 2026 assets and articles as historical references. Do not rename an
  old flyer to 2027 or silently change the dates on an archived article.
- Shared assets such as the official logo remain in their existing shared
  locations and are linked from each edition's register.
- Existing artist and hotel media can support the current design. A previous
  edition's artist booking, hotel rate, room allocation, pass, or checkout does
  not become a confirmed 2027 offer through reuse.
- This repository is a website publication source. Catalog only public-safe
  material here. Keep private agreements, personal lists, credentials, account
  details, and internal drafts outside publishable files; the existing ignored
  `output/` directory is available for local working drafts.
- Leave changes local unless the owner explicitly requests publication, as
  required by the [delivery rules](../.agent/rules/delivery.md#publication).
