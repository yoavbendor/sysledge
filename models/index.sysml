package SysledgeIndex {
    doc /*
     * Top-level entry point for the sysledge knowledge base — the first file an agent reads to
     * discover what systems are modeled. Import a system's packages here as it is added.
     *
     * Systems modeled:
     *   - nanos3reader  (pilot)  — minimal read-only S3 range reader for C++
     * Planned (from GitLab): nanotins, nanolance, nanoarrow2parquet, then HW/embedded systems.
     */
    import Concepts::*;
    import Nanos3readerRequirements::*;
    import Nanos3readerStructure::*;
    import Nanos3readerBehavior::*;
    import Nanos3readerVerification::*;
    import Nanos3readerAllocation::*;
}
