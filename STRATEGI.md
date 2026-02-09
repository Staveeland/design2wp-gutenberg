# Zocial × Workflows — WordPress AI Web Builder

## Konsept

AI-drevet nettsidebygging: Figma-design → automatisk generert WordPress-side → kunden redigerer selv.

## Arkitektur

```
Figma (design) → AI Vision-analyse → Gutenberg/Kadence blocks → WordPress REST API → Ferdig side
```

### Stack

| Lag | Teknologi | Rolle |
|-----|-----------|-------|
| **CMS** | WordPress | Innholdsstyring, brukerredigering |
| **Tema** | Kadence Pro | Base-styling, header/footer builder, responsivt |
| **Blokker** | Kadence Blocks + Gutenberg core | Sideinnhold, seksjoner, layout |
| **Felter/backend** | ACF Pro | Strukturerte datatyper (eiendommer, teammedlemmer, tjenester, etc.) |
| **API** | REST API eller WPGraphQL | Datautveksling mellom AI-pipeline og WordPress |
| **AI** | GPT-4o Vision | Analyserer Figma-design, genererer blokk-markup |
| **Design** | Figma | Zocials designere jobber som før |

## REST API vs WPGraphQL

| | REST API | WPGraphQL |
|---|---------|-----------|
| **Oppsett** | Innebygd i WordPress | Plugin (gratis) |
| **Spørringer** | Flere requests for relatert data | Én request, hent akkurat det du trenger |
| **Skriving** | Full støtte (POST/PUT/DELETE) | Mutations støttet, men mindre modent |
| **ACF-integrasjon** | Fungerer ut av boksen | Trenger WPGraphQL for ACF (gratis plugin) |
| **Kadence** | Blokker lagres som post_content — fungerer | Samme — blokker er i content |
| **Headless** | Fungerer, men overfetcher | Perfekt for headless (presis datahenting) |
| **Kompleksitet** | Enklere å debugge | Krever GraphQL-kunnskap |

**Anbefaling:** REST API for AI-pipelinen (skriving/publisering). Legg til WPGraphQL senere kun hvis dere går headless for spesifikke kunder.

## Arbeidsflyt

### 1. Design (Zocial)
- Designer lager nettside i Figma som normalt
- Eksporterer som PNG/PDF, eller vi henter direkte via Figma API

### 2. AI-konvertering (Workflows)
- GPT-4o Vision analyserer designet
- Identifiserer seksjoner, farger, fonts, layout, innhold
- Genererer Kadence/Gutenberg block markup
- Oppretter ACF-felter for dynamisk innhold

### 3. Publisering (automatisk)
- Block markup sendes til WordPress via REST API
- Bilder lastes opp til Media Library
- Side opprettes som draft → kunden/Zocial reviewer

### 4. Redigering (kunden)
- Kunden åpner WordPress
- Ser ferdig side med alle blokker
- Redigerer tekst, bilder, farger visuelt
- Ingen kode nødvendig

## ACF-bruk

ACF bygger strukturerte felter for repeterende innhold:

**Eksempel — Eiendomsside:**
```
Eiendom (Custom Post Type)
├── Navn (tekst)
├── Adresse (tekst)
├── Areal (nummer)
├── Bilder (galleri)
├── Status (select: ledig/utleid)
├── Leietaker (relasjon → Leietaker CPT)
└── Beskrivelse (wysiwyg)
```

Kunden fyller ut feltene → Kadence-template viser det automatisk. AI kan også populere via API.

**Typiske ACF-oppsett per bransje:**
- **Eiendom:** Eiendommer, leietakere, kontaktpersoner
- **Restaurant:** Meny, åpningstider, bestilling
- **Butikk:** Produkter, kampanjer, ansatte
- **Klinikk:** Tjenester, priser, behandlere, booking

## Prismodell (forslag til Zocial)

| Pakke | Hva | Pris |
|-------|-----|------|
| **Standard** | Figma → AI → WordPress + Kadence + opplæring | 15-25K oppsett + 2K/mnd hosting/vedlikehold |
| **Utvidet** | + ACF custom post types + dynamisk innhold | 25-40K oppsett + 3K/mnd |
| **Premium** | + WPGraphQL headless + custom frontend | 40-60K oppsett + 5K/mnd |

## Neste steg

1. ~~Prototype med Gutenberg core blocks~~ ✅
2. ~~Test med Kadence Blocks~~ 🔄 Pågår
3. Sett opp ACF-felter for Haugli Eiendom (eiendommer, leietakere)
4. Bygg komplett Haugli-side med alle undersider
5. Dokumenter pipeline for Zocial-designere
6. Test med et nytt design (ikke Haugli) for å validere at det er generisk
