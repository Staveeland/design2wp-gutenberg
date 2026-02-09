# Design2WP — Build Prompt

## Hva dette er
Et AI-drevet verktøy som konverterer Figma-design til ferdige WordPress-sider med Kadence Blocks. Python-backend, trenger web-UI.

## Eksisterende kode (~/projects/design2wp-gutenberg/)
- `vision_analyzer.py` — GPT-4o Vision analyserer design-screenshots → strukturert JSON (seksjoner, farger, fonts, layout)
- `gutenberg_blocks.py` — 13 block-generatorer (heading, paragraph, columns, image, cover, buttons, group, spacer, separator, list, quote, media-text)
- `converter.py` — Layout JSON → Gutenberg/Kadence block markup + Block Patterns
- `wp_publisher.py` — WordPress REST API (create/update pages, upload media, cookie-auth)
- `main.py` — CLI: `python3 main.py --image screenshot.png --publish --wp-url ... --wp-user ... --wp-pass ...`
- `STRATEGI.md` — Full strategi-dokument for Zocial × Workflows

## Hva som skal bygges

### Web-applikasjon med dette flowet:

**1. Prosjekter**
- Opprett nytt prosjekt (kundenavn, WordPress-URL, credentials)
- Liste over eksisterende prosjekter

**2. Design-upload**
- Last opp Figma-screenshots (PNG/JPG/PDF) eller hent via Figma API (token + fil-ID)
- Vis uploaded designs i et galleri

**3. AI-analyse**
- Klikk "Analyser" → GPT-4o Vision analyserer designet
- Vis resultatet: identifiserte seksjoner, farger, fonts, layout-struktur
- Mulighet for å redigere/justere analysen manuelt

**4. Generer WordPress-sider**
- Klikk "Generer" → konverterer analyse til Kadence/Gutenberg blocks
- Preview av generert markup (rendered HTML)
- Velg side-type: ny side eller oppdater eksisterende

**5. Publiser til WordPress**
- Klikk "Publiser" → sender til WordPress via REST API
- Last opp bilder automatisk til Media Library
- Vis status: publisert, draft, feilet

**6. Historikk**
- Logg over alle genereringer og publiseringer
- Mulighet for å rulle tilbake

### Tech-stack forslag
- **Frontend:** Next.js eller SvelteKit (moderne, raskt)
- **Backend:** Eksisterende Python-scripts wrappet i FastAPI, eller port til TypeScript
- **Database:** SQLite for prosjekter/historikk (enkel start)
- **Auth:** Enkel login (dette er internt verktøy for Zocial/Workflows)
- **Hosting:** Kan kjøre lokalt eller på en VPS

### WordPress-integrasjon
- Kadence Pro + Kadence Blocks (allerede installert)
- Rank Math for SEO (auto-generert meta)
- ACF Pro for strukturerte felter (custom post types)
- REST API for all kommunikasjon

### Viktige detaljer
- Kadence-blokker MÅ ha `uniqueID` attributt (random string) — uten det krasjer editoren
- Etter API-publisering må blokkene "gjenopprettes" i editoren (kjent Gutenberg-validerings-issue)
- Farger fra Haugli-designet: mørk brun #3B2314, orange #E8731A
- GPT-4o Vision brukes via OpenAI API (trenger OPENAI_API_KEY)

### Test-miljø
- WordPress: http://kvilhaugsvik.no.datasenter.no/wp-admin/
- Login: zocialas / Pajero_333
- Eksisterende test-side: page ID 339 (haugli-eiendom-forside)
- Bilder allerede i Media Library

### Figma API (valgfritt)
- Token: Se TOOLS.md
- Kan hente frames, bilder, farger, fonts direkte fra Figma-fil
- Mer presist enn screenshots

## Mål
Et verktøy Zocial-designere kan bruke uten teknisk kompetanse: last opp design → få ferdig WordPress-side.
