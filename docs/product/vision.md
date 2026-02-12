---
title: FeedbackAI -- Vision
created: 2026-02-12
status: active
---

# Vision: FeedbackAI bei Zipmend

## In einem Satz

FeedbackAI macht qualitative Nutzerforschung bei Zipmend zum Standard -- fuer jedes Produkt, jede Zielgruppe, jederzeit abrufbar.

## Das Problem

Zipmend hat drei digitale Produkte mit drei verschiedenen Nutzergruppen. Feedback kommt heute unsystematisch: ein Ticket hier, ein Anruf dort, eine Vermutung im Meeting. Niemand weiss wirklich, was Carrier frustriert, wo Shipper im Buchungsprozess haengen bleiben, oder welche Workarounds Disponenten sich gebaut haben.

Klassische Surveys (NPS, Formulare) liefern Zahlen, aber kein Verstaendnis. Echte Interviews skalieren nicht -- ein UX-Researcher fuer drei Produkte und hunderte Nutzer ist nicht machbar.

## Die Loesung

Ein KI-Interviewer, der wie ein Senior UX-Researcher Gespraeche fuehrt: offen, nicht-fuehrend, kontextbewusst. Er kennt das Produkt, die Zielgruppe und das Szenario -- und stellt genau die richtigen Nachfragen.

Die Ergebnisse (Transkripte, Zusammenfassungen, extrahierte Facts) fliessen in ein Dashboard, das Muster sichtbar macht und Produktentscheidungen stuetzt.

## Drei Produkte, drei Welten

| Produkt | Zielgruppe | Kontext |
|---------|-----------|---------|
| **Carrier View** | Carrier (externe Partner) | Transport-Marktplatz, Bidding, Fahrzeugverwaltung |
| **Booking Platform** | Shipper (Kunden) | Buchungsprozess, Preisrechner, Transparenz |
| **Express Panel** | Disponenten (intern) | Transportzuweisung, Tagesgeschaeft, Workflows |

Jede Welt hat eigene Schmerzpunkte, eigene Sprache, eigene Erwartungen. Der Interviewer passt sich an -- selber Kern-Prompt, aber unterschiedliche Company/Product/Scenario-Kontexte.

## Szenarien

| Szenario | Ziel |
|----------|------|
| **Pain Point Discovery** | Konkrete Probleme und deren Impact identifizieren |
| **Satisfaction Research** | Zufriedenheit messen, Verbesserungsprioritaeten finden |
| *(spaeter weitere)* | Feature Validation, Onboarding Research, Churn Analysis... |

## Interview-Kanaele

| Kanal | Wann | Fuer wen |
|-------|------|----------|
| **Embedded Widget** | Nutzer ist gerade im Produkt | Carrier, Shipper |
| **Email-Einladung** | Gezielt nach bestimmter Erfahrung | Alle Gruppen |
| **Voice** | Nutzer will nicht tippen (Carrier unterwegs, Disponenten im Stress) | Alle Gruppen |

## Insights-Pipeline

```
Interview (Text/Voice)
    |
    v
Transkript + Zusammenfassung
    |
    v
Fact Extraction (atomare Aussagen)
    |
    v
LLM-Clustering (thematische Muster)
    |
    v
Dashboard (pro Produkt + Cross-Product)
```

Optional: Session Recordings (Microsoft Clarity o.ae.) als zusaetzlicher Kontext -- der Interviewer weiss nicht nur was der Nutzer sagt, sondern sieht auch was er tut.

## Prinzipien

1. **Ein Schritt nach dem anderen.** Immer das naechst-wichtigste zuerst. Kein Feature ohne validierten Bedarf.
2. **Jede Phase liefert Wert.** Wenn nach Phase X Schluss ist, muss das Ergebnis trotzdem nuetzlich sein.
3. **Qualitaet vor Quantitaet.** Ein gutes Interview mit echten Insights schlaegt 100 NPS-Scores.
4. **Anti-Leading ist Kernprinzip.** Der Interviewer fragt nach Verhalten und Erfahrungen, nie nach Wuenschen oder hypothetischen Features.
5. **Context is King.** Je besser der Interviewer das Produkt und die Zielgruppe kennt, desto bessere Fragen stellt er.

## Strategische Perspektive

Zipmend ist der erste Kunde. FeedbackAI wird hier gebaut, getestet und validiert. Wenn das System fuer drei Produkte mit drei Zielgruppen funktioniert, ist die Architektur multi-tenant-faehig.

Moegliche Zukunft: SaaS-Ausgruendung -- jedes Unternehmen mit digitalen Produkten hat dasselbe Problem. Aber das ist nicht Phase 1. Phase 1 ist: **ein Carrier fuehrt ein Interview, und die Zusammenfassung ist brauchbar.**

## Phasen-Ueberblick

| Phase | Was | Wert |
|-------|-----|------|
| **MVP** | Carrier Widget + Backend + Supabase | Erster Interview-Loop funktioniert |
| **Multi-Context** | Drei Produkte, dynamische Kontexte | Alle Zipmend-Bereiche abgedeckt |
| **Email-Einladungen** | Gezielte Research-Kampagnen | Systematische Datenerhebung |
| **Dashboard** | Insights sichtbar machen | Feedback-to-Decision Loop geschlossen |
| **Voice** | Sprachinterviews | Hoehere Qualitaet, weniger Friction |
| **Session Context** | Recordings als Zusatzkontext | Interviewer versteht Verhalten + Worte |

Priorisierung: MVP → Multi-Context → Email → Dashboard → Voice → Session Context.
Voice ist wertvoll, aber Email + Dashboard schliessen den Loop schneller: Interviews verschicken → Daten sammeln → Insights sehen → Entscheidungen treffen.
