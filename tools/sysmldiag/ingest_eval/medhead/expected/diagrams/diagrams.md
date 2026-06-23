# MedHead — model diagrams

_Generated from the SysML knowledge graph by `tools/sysmldiag`. Do not hand-edit — re-run the generator._

## Contents

- [Requirements traceability](#requirements-traceability) — Which part satisfies which requirement, and which is verified.
- [Block definition diagram](#block-definition-diagram) — Part definitions, their attributes/ports, inheritance and composition.
- [Internal connections (IBD)](#internal-connections-ibd) — Ports and the connections wiring parts together.
- [Behavior (actions)](#behavior-actions) — Action decomposition and parameters.
- [Model map (packages)](#model-map-packages) — Every package and the definitions it contains, by RFLP layer.
- [Allocation (RFLP overview)](#allocation-rflp-overview) — Which implementation part realizes which requirement, across layers.

## Requirements traceability

Which part satisfies which requirement, and which is verified.

*Blue rounded = component, purple = verification case. Green requirement = verified, amber = satisfied-but-unverified, grey = orphan.*

[View as SVG](svg/requirements.svg)

```mermaid
flowchart LR
  classDef verified fill:#d5f5e3,stroke:#27ae60,color:#145a32;
  classDef partial  fill:#fdebd0,stroke:#e67e22,color:#7e5109;
  classDef orphan   fill:#f2f3f4,stroke:#85929e,color:#424949;
  classDef part     fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;
  classDef vcase    fill:#f4ecf7,stroke:#8e44ad,color:#4a235a;
  P_eventBus(["eventBus"]):::part
  R_FaultTolerance["FaultTolerance"]:::partial
  P_eventBus -->|satisfies| R_FaultTolerance
  P_integrationLayer(["integrationLayer"]):::part
  R_NhsInteroperability["NhsInteroperability"]:::partial
  P_integrationLayer -->|satisfies| R_NhsInteroperability
  P_patientInformation(["patientInformation"]):::part
  R_GdprAdherence["GdprAdherence"]:::partial
  P_patientInformation -->|satisfies| R_GdprAdherence
  P_scheduling(["scheduling"]):::part
  R_SubSecondBedAvailability["SubSecondBedAvailability"]:::partial
  P_scheduling -->|satisfies| R_SubSecondBedAvailability
  P_serviceMesh(["serviceMesh"]):::part
  R_ZeroDisruptionMigration["ZeroDisruptionMigration"]:::partial
  P_serviceMesh -->|satisfies| R_ZeroDisruptionMigration
  R_MedHead__FaultTolerance["FaultTolerance"]:::orphan
  R_MedHead__GdprAdherence["GdprAdherence"]:::orphan
  R_MedHead__NhsInteroperability["NhsInteroperability"]:::orphan
  R_MedHead__SubSecondBedAvailability["SubSecondBedAvailability"]:::orphan
  R_MedHead__ZeroDisruptionMigration["ZeroDisruptionMigration"]:::orphan
```

> ⚠️ 5 requirement(s) are satisfied but not verified (amber) — candidate gaps for new verification cases.
> ⚠️ 5 requirement(s) are neither satisfied nor verified (grey).

<details><summary>Source elements</summary>

| Element | Source |
|---|---|
| `FaultTolerance` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:24` |
| `GdprAdherence` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:18` |
| `NhsInteroperability` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:12` |
| `SubSecondBedAvailability` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:36` |
| `ZeroDisruptionMigration` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:30` |

</details>


## Block definition diagram

Part definitions, their attributes/ports, inheritance and composition.

*`<|--` = specialization (variant backend), `*--` = composition (owned part). «port»/«interface» tag connection points.*

[View as SVG](svg/bdd.svg)

```mermaid
classDiagram
  class AccessUsabilityLayer["AccessUsabilityLayer"] {
    +accessControl : String
    +userInterfaces : String
  }
  class Appointments["Appointments"] {
    +bookingRecords : String
    +events : «port» EventPort
  }
  class ClientAccessTier["ClientAccessTier"] {
    +clientEndpoints : String
  }
  class DataLake["DataLake"] {
    +analyticsData : String
    +ingest : «port» DataIngestPort
  }
  class EmergencySystemsTier["EmergencySystemsTier"] {
    +emergencyProtocols : String
    +failoverMechanisms : String
  }
  class EventBus["EventBus"] {
    +eventTopics : String
    +feed : «port» EventPort
  }
  class IntegrationLayer["IntegrationLayer"] {
    +complianceFramework : String
    +externalIntegrations : String
  }
  class MedHeadSystem["MedHeadSystem"] {
  }
  class MedicalHistory["MedicalHistory"] {
    +clinicalRecords : String
    +events : «port» EventPort
  }
  class MedicalSpecialist["MedicalSpecialist"] {
    +events : «port» EventPort
    +practitionerId : String
    +specialisms : String
  }
  class PatientInformation["PatientInformation"] {
    +demographics : String
    +events : «port» EventPort
    +patientId : String
  }
  class ProviderManagement["ProviderManagement"] {
    +capabilities : String
    +events : «port» EventPort
    +providerId : String
  }
  class Rosters["Rosters"] {
    +events : «port» EventPort
    +onCallAssignments : String
    +rosterData : String
  }
  class Scheduling["Scheduling"] {
    +allocationStrategy : String
    +bedAvailability : String
    +events : «port» EventPort
  }
  class ServiceMesh["ServiceMesh"] {
    +proxyConfig : String
  }
  class Specialism["Specialism"] {
    +events : «port» EventPort
    +specialismCatalogue : String
  }
  MedHeadSystem *-- AccessUsabilityLayer : accessUsabilityLayer
  MedHeadSystem *-- Appointments : appointments
  MedHeadSystem *-- ClientAccessTier : clientAccessTier
  MedHeadSystem *-- DataLake : dataLake
  MedHeadSystem *-- EmergencySystemsTier : emergencySystemsTier
  MedHeadSystem *-- EventBus : eventBus
  MedHeadSystem *-- IntegrationLayer : integrationLayer
  MedHeadSystem *-- MedicalHistory : medicalHistory
  MedHeadSystem *-- MedicalSpecialist : medicalSpecialist
  MedHeadSystem *-- PatientInformation : patientInformation
  MedHeadSystem *-- ProviderManagement : providerManagement
  MedHeadSystem *-- Rosters : rosters
  MedHeadSystem *-- Scheduling : scheduling
  MedHeadSystem *-- ServiceMesh : serviceMesh
  MedHeadSystem *-- Specialism : specialism
```

<details><summary>Source elements</summary>

| Element | Source |
|---|---|
| `AccessUsabilityLayer` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:120` |
| `Appointments` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:83` |
| `ClientAccessTier` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:115` |
| `DataLake` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:103` |
| `EmergencySystemsTier` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:126` |
| `EventBus` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:97` |
| `IntegrationLayer` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:132` |
| `MedHeadSystem` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:146` |
| `MedicalHistory` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:50` |
| `MedicalSpecialist` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:62` |
| `PatientInformation` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:43` |
| `ProviderManagement` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:69` |
| `Rosters` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:89` |
| `Scheduling` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:76` |
| `ServiceMesh` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:109` |
| `Specialism` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:56` |

</details>


## Internal connections (IBD)

Ports and the connections wiring parts together.

*Yellow = port/interface. `<-->` = a modeled connection.*

[View as SVG](svg/ibd.svg)

```mermaid
flowchart LR
  classDef port fill:#fef9e7,stroke:#b7950b,color:#7d6608;
  classDef part fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;
  PT_appointments_events(["appointments.events"]):::port
  PT_eventBus_feed(["eventBus.feed"]):::port
  PT_appointments_events <--> PT_eventBus_feed
  PT_dataLake_ingest(["dataLake.ingest"]):::port
  PT_eventBus_feed <--> PT_dataLake_ingest
  PT_medicalHistory_events(["medicalHistory.events"]):::port
  PT_medicalHistory_events <--> PT_eventBus_feed
  PT_medicalSpecialist_events(["medicalSpecialist.events"]):::port
  PT_medicalSpecialist_events <--> PT_eventBus_feed
  PT_patientInformation_events(["patientInformation.events"]):::port
  PT_patientInformation_events <--> PT_eventBus_feed
  PT_providerManagement_events(["providerManagement.events"]):::port
  PT_providerManagement_events <--> PT_eventBus_feed
  PT_rosters_events(["rosters.events"]):::port
  PT_rosters_events <--> PT_eventBus_feed
  PT_scheduling_events(["scheduling.events"]):::port
  PT_scheduling_events <--> PT_eventBus_feed
  PT_specialism_events(["specialism.events"]):::port
  PT_specialism_events <--> PT_eventBus_feed
  PT_MedHead__Appointments__events(["events"]):::port
  PT_MedHead__DataLake__ingest(["ingest"]):::port
  PT_MedHead__EventBus__feed(["feed"]):::port
  PT_MedHead__MedicalHistory__events(["events"]):::port
  PT_MedHead__MedicalSpecialist__events(["events"]):::port
  PT_MedHead__PatientInformation__events(["events"]):::port
  PT_MedHead__ProviderManagement__events(["events"]):::port
  PT_MedHead__Rosters__events(["events"]):::port
  PT_MedHead__Scheduling__events(["events"]):::port
  PT_MedHead__Specialism__events(["events"]):::port
```

> ⚠️ 9 connection(s) across 10 declared port(s). Interconnection is under-modeled — add `connect` statements to complete the IBD.

<details><summary>Source elements</summary>

| Element | Source |
|---|---|
| `events` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:48` |
| `events` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:54` |
| `events` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:60` |
| `events` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:67` |
| `events` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:74` |
| `events` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:81` |
| `events` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:87` |
| `events` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:94` |
| `feed` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:101` |
| `ingest` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:107` |

</details>


## Behavior (actions)

Action decomposition and parameters.

*Teal = action, grey rounded = parameter. Solid = sub-action.*

[View as SVG](svg/behavior.svg)

```mermaid
flowchart TD
  classDef act fill:#e8f8f5,stroke:#16a085,color:#0e6251;
  classDef param fill:#fdfefe,stroke:#aab7b8,color:#566573;
  A_MedHead__AllocateBed["AllocateBed"]:::act
  PM_MedHead__AllocateBed__request(["request"]):::param
  A_MedHead__AllocateBed -.->|param| PM_MedHead__AllocateBed__request
  PM_MedHead__AllocateBed__reservation(["reservation"]):::param
  A_MedHead__AllocateBed -.->|param| PM_MedHead__AllocateBed__reservation
```

> ⚠️ Execution order (succession/flow) is not modeled yet — edges show containment/parameters only. Add `then`/`succession` to get a true flow.

<details><summary>Source elements</summary>

| Element | Source |
|---|---|
| `AllocateBed` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:139` |

</details>


## Model map (packages)

Every package and the definitions it contains, by RFLP layer.

*Colour = RFLP layer. Definitions per layer — Requirements: 5, Logical: 25.*

[View as SVG](svg/package_map.svg)

```mermaid
flowchart TD
  classDef lreq fill:#fdedec,stroke:#cb4335,color:#7b241c;
  classDef lfun fill:#fef5e7,stroke:#ca6f1e,color:#7e5109;
  classDef llog fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;
  classDef lphy fill:#eafaf1,stroke:#229954,color:#145a32;
  classDef lnone fill:#f4f6f7,stroke:#909497,color:#515a5a;
  subgraph pkg_Concepts["Concepts"]
    Concepts__ByteRangeReadPort["ByteRangeReadPort"]:::llog
    Concepts__ByteRangeReadStream["ByteRangeReadStream"]:::llog
    Concepts__CredentialSourcePort["CredentialSourcePort"]:::llog
    Concepts__Provenance["Provenance"]:::lnone
  end
  subgraph pkg_MedHead["MedHead"]
    MedHead__AccessUsabilityLayer["AccessUsabilityLayer"]:::llog
    MedHead__AllocateBed["AllocateBed"]:::lnone
    MedHead__Appointments["Appointments"]:::llog
    MedHead__ClientAccessTier["ClientAccessTier"]:::llog
    MedHead__DataIngestPort["DataIngestPort"]:::llog
    MedHead__DataLake["DataLake"]:::llog
    MedHead__EmergencySystemsTier["EmergencySystemsTier"]:::llog
    MedHead__EventBus["EventBus"]:::llog
    MedHead__EventPort["EventPort"]:::llog
    MedHead__FaultTolerance["FaultTolerance"]:::lreq
    MedHead__GdprAdherence["GdprAdherence"]:::lreq
    MedHead__IntegrationLayer["IntegrationLayer"]:::llog
    MedHead__MedHeadSystem["MedHeadSystem"]:::llog
    MedHead__MedicalHistory["MedicalHistory"]:::llog
    MedHead__MedicalSpecialist["MedicalSpecialist"]:::llog
    MedHead__NhsInteroperability["NhsInteroperability"]:::lreq
    MedHead__PatientInformation["PatientInformation"]:::llog
    MedHead__ProviderManagement["ProviderManagement"]:::llog
    MedHead__Rosters["Rosters"]:::llog
    MedHead__Scheduling["Scheduling"]:::llog
    MedHead__ServiceMesh["ServiceMesh"]:::llog
    MedHead__Specialism["Specialism"]:::llog
    MedHead__SubSecondBedAvailability["SubSecondBedAvailability"]:::lreq
    MedHead__ZeroDisruptionMigration["ZeroDisruptionMigration"]:::lreq
  end
  subgraph pkg_ScalarValues["ScalarValues"]
    ScalarValues__Boolean["Boolean"]:::llog
    ScalarValues__Integer["Integer"]:::llog
    ScalarValues__Real["Real"]:::llog
    ScalarValues__String["String"]:::llog
  end
```

<details><summary>Source elements</summary>

| Element | Source |
|---|---|
| `AccessUsabilityLayer` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:120` |
| `AllocateBed` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:139` |
| `Appointments` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:83` |
| `Boolean` | `lib/scalar_values.sysml:12` |
| `ByteRangeReadPort` | `lib/concepts.sysml:27` |
| `ByteRangeReadStream` | `lib/concepts.sysml:31` |
| `ClientAccessTier` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:115` |
| `CredentialSourcePort` | `lib/concepts.sysml:39` |
| `DataIngestPort` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:10` |
| `DataLake` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:103` |
| `EmergencySystemsTier` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:126` |
| `EventBus` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:97` |
| `EventPort` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:9` |
| `FaultTolerance` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:24` |
| `GdprAdherence` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:18` |
| `Integer` | `lib/scalar_values.sysml:11` |
| `IntegrationLayer` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:132` |
| `MedHeadSystem` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:146` |
| `MedicalHistory` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:50` |
| `MedicalSpecialist` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:62` |
| `NhsInteroperability` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:12` |
| `PatientInformation` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:43` |
| `Provenance` | `lib/concepts.sysml:15` |
| `ProviderManagement` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:69` |
| `Real` | `lib/scalar_values.sysml:10` |
| `Rosters` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:89` |
| `Scheduling` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:76` |
| `ServiceMesh` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:109` |
| `Specialism` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:56` |
| `String` | `lib/scalar_values.sysml:9` |
| `SubSecondBedAvailability` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:36` |
| `ZeroDisruptionMigration` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:30` |

</details>


## Allocation (RFLP overview)

Which implementation part realizes which requirement, across layers.

*Red = requirement, blue = implementing part. Arrow = satisfies.*

[View as SVG](svg/allocation.svg)

```mermaid
flowchart LR
  classDef req fill:#fdedec,stroke:#cb4335,color:#7b241c;
  classDef impl fill:#eaf2f8,stroke:#2980b9,color:#1b4f72;
  subgraph impl["Implementation (Logical/Physical)"]
  I_eventBus(["eventBus"]):::impl
  I_integrationLayer(["integrationLayer"]):::impl
  I_patientInformation(["patientInformation"]):::impl
  I_scheduling(["scheduling"]):::impl
  I_serviceMesh(["serviceMesh"]):::impl
  end
  subgraph reqs["Requirements"]
  R_FaultTolerance["FaultTolerance"]:::req
  R_GdprAdherence["GdprAdherence"]:::req
  R_NhsInteroperability["NhsInteroperability"]:::req
  R_SubSecondBedAvailability["SubSecondBedAvailability"]:::req
  R_ZeroDisruptionMigration["ZeroDisruptionMigration"]:::req
  end
  I_eventBus -->|satisfies| R_FaultTolerance
  I_integrationLayer -->|satisfies| R_NhsInteroperability
  I_patientInformation -->|satisfies| R_GdprAdherence
  I_scheduling -->|satisfies| R_SubSecondBedAvailability
  I_serviceMesh -->|satisfies| R_ZeroDisruptionMigration
```

> ⚠️ 5 satisfy link(s) binding parts to 5 requirement(s).

<details><summary>Source elements</summary>

| Element | Source |
|---|---|
| `FaultTolerance` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:24` |
| `GdprAdherence` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:18` |
| `NhsInteroperability` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:12` |
| `SubSecondBedAvailability` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:36` |
| `ZeroDisruptionMigration` | `tools/sysmldiag/ingest_eval/medhead/expected/medhead.sysml:30` |

</details>

