# MedHead platform — distilled architecture brief (test fixture)

> Provenance: paraphrased from the public OpenClassrooms "Software-Architect-P11"
> Architecture Definition Document
> (github.com/OpenClassrooms-Student-Center/Software-Architect-P11, `master`).
> This file is an original paraphrase written for testing the diagram generator;
> no text is copied from the source. It is a **test fixture**, not part of the
> nano* knowledge base, and everything extracted from it is `maturity = "concept"`.

## System
MedHead is a patient-centric healthcare platform that consolidates scheduling,
appointments and emergency response across four previously separate organisations.
It replaces legacy systems with an event-driven set of microservices.

## Bounded contexts (candidate blocks)
- **Patient Information** — owns patient demographics and identity.
- **Medical History** — owns longitudinal clinical records.
- **Specialism** — catalogue of medical specialisms.
- **Medical Specialist** — practitioners and their specialisms.
- **Provider Management** — hospitals/clinics and their capabilities.
- **Scheduling** — availability and bed allocation.
- **Appointments** — booking and consolidation of appointments.
- **Rosters** — staff rota and on-call assignment.

## Connections
Services communicate over a central **event bus** (publish/subscribe); a shared
**data lake** ingests events for analytics. A service mesh with side-car proxies
fronts each service.

## Deployment tiers
1. Client access tier (web/mobile clients).
2. Access & usability layer (API gateway, mesh).
3. Emergency systems tier (bed allocation, responder dispatch).
4. Integration layer (event bus, data lake, legacy adapters).

## A workflow (behavior)
Emergency bed allocation: a responder requests a bed → Scheduling queries bed
availability across providers → selects the nearest suitable bed → reserves it →
notifies the responder and updates Rosters.

## Requirements
- NHS Digital interoperability compliance.
- GDPR adherence for patient data.
- Fault tolerance with no single point of failure.
- Zero disruption to production during migration.
- Sub-second bed-availability query response.
