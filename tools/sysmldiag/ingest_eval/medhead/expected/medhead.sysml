// SNAPSHOT — not part of the nano* knowledge base, not a CI golden.
// Extracted from ../source.md by Claude Haiku 4.5 (Layer B ingestion eval); one
// non-deterministic run, kept as a "doc -> model -> diagram" showcase. All facts
// are maturity = "concept". See ./README.md.
package MedHead {
    import Concepts::*;
    import ScalarValues::*;

    port def EventPort { doc /* publish/subscribe to the event bus */ }
    port def DataIngestPort { doc /* ingest events and data to the data lake */ }

    requirement def <'MH-1'> NhsInteroperability {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* The platform shall comply with NHS Digital interoperability standards */
        attribute id : String = "MH-1";
        attribute text : String = "The platform shall comply with NHS Digital interoperability standards";
    }
    requirement def <'MH-2'> GdprAdherence {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* The platform shall adhere to GDPR for patient data protection */
        attribute id : String = "MH-2";
        attribute text : String = "The platform shall adhere to GDPR for patient data protection";
    }
    requirement def <'MH-3'> FaultTolerance {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* The platform shall provide fault tolerance with no single point of failure */
        attribute id : String = "MH-3";
        attribute text : String = "The platform shall provide fault tolerance with no single point of failure";
    }
    requirement def <'MH-4'> ZeroDisruptionMigration {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* The platform shall achieve zero disruption to production during migration */
        attribute id : String = "MH-4";
        attribute text : String = "The platform shall achieve zero disruption to production during migration";
    }
    requirement def <'MH-5'> SubSecondBedAvailability {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* The platform shall respond to bed-availability queries in sub-second latency */
        attribute id : String = "MH-5";
        attribute text : String = "The platform shall respond to bed-availability queries in sub-second latency";
    }

    part def PatientInformation {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Owns patient demographics and identity data */
        attribute patientId : String;
        attribute demographics : String;
        port events : EventPort;
    }
    part def MedicalHistory {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Manages longitudinal clinical records */
        attribute clinicalRecords : String;
        port events : EventPort;
    }
    part def Specialism {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Maintains catalogue of medical specialisms */
        attribute specialismCatalogue : String;
        port events : EventPort;
    }
    part def MedicalSpecialist {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Manages practitioners and their specialisms */
        attribute practitionerId : String;
        attribute specialisms : String;
        port events : EventPort;
    }
    part def ProviderManagement {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Manages hospitals, clinics and their capabilities */
        attribute providerId : String;
        attribute capabilities : String;
        port events : EventPort;
    }
    part def Scheduling {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Manages availability and bed allocation */
        attribute bedAvailability : String;
        attribute allocationStrategy : String;
        port events : EventPort;
    }
    part def Appointments {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Manages booking and consolidation */
        attribute bookingRecords : String;
        port events : EventPort;
    }
    part def Rosters {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Manages staff rota and on-call assignments */
        attribute rosterData : String;
        attribute onCallAssignments : String;
        port events : EventPort;
    }

    part def EventBus {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Central event bus for publish/subscribe communication */
        attribute eventTopics : String;
        port feed : EventPort;
    }
    part def DataLake {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Ingests events for analytics and historical analysis */
        attribute analyticsData : String;
        port ingest : DataIngestPort;
    }
    part def ServiceMesh {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Service mesh with side-car proxies for inter-service communication */
        attribute proxyConfig : String;
    }

    part def ClientAccessTier {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Client-facing access layer */
        attribute clientEndpoints : String;
    }
    part def AccessUsabilityLayer {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Access control and usability layer */
        attribute accessControl : String;
        attribute userInterfaces : String;
    }
    part def EmergencySystemsTier {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Emergency response systems tier */
        attribute emergencyProtocols : String;
        attribute failoverMechanisms : String;
    }
    part def IntegrationLayer {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Integration with external systems and NHS Digital compliance */
        attribute externalIntegrations : String;
        attribute complianceFramework : String;
    }

    action def AllocateBed {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Emergency bed allocation workflow */
        in request : String;
        out reservation : String;
    }

    part def MedHeadSystem {
        @Provenance { source = "OpenClassrooms/Software-Architect-P11:MedHead-ADD"; maturity = "concept"; }
        doc /* Patient-centric healthcare platform */

        part patientInformation : PatientInformation;
        part medicalHistory : MedicalHistory;
        part specialism : Specialism;
        part medicalSpecialist : MedicalSpecialist;
        part providerManagement : ProviderManagement;
        part scheduling : Scheduling;
        part appointments : Appointments;
        part rosters : Rosters;
        part eventBus : EventBus;
        part dataLake : DataLake;
        part serviceMesh : ServiceMesh;
        part clientAccessTier : ClientAccessTier;
        part accessUsabilityLayer : AccessUsabilityLayer;
        part emergencySystemsTier : EmergencySystemsTier;
        part integrationLayer : IntegrationLayer;

        connect patientInformation.events to eventBus.feed;
        connect medicalHistory.events to eventBus.feed;
        connect specialism.events to eventBus.feed;
        connect medicalSpecialist.events to eventBus.feed;
        connect providerManagement.events to eventBus.feed;
        connect scheduling.events to eventBus.feed;
        connect appointments.events to eventBus.feed;
        connect rosters.events to eventBus.feed;
        connect eventBus.feed to dataLake.ingest;

        satisfy NhsInteroperability by integrationLayer;
        satisfy GdprAdherence by patientInformation;
        satisfy FaultTolerance by eventBus;
        satisfy ZeroDisruptionMigration by serviceMesh;
        satisfy SubSecondBedAvailability by scheduling;
    }
}
