package Nanos3readerAllocation {
    doc /*
     * Traceability: which component satisfies which requirement. This is the "facts" backbone an
     * advisory agent follows to answer "is requirement X actually implemented, and by what?".
     * satisfy targets the requirement definitions directly (nomograph's completeness checks are
     * definition-centric), binding each to the part that realizes it, all at nanos3reader@ff28f0b.
     */
    import Concepts::*;
    import Nanos3readerRequirements::*;
    import Nanos3readerStructure::*;

    // The system as a whole, realized by S3MinStreamFactory; satisfy links bind requirements to parts.
    part def Nanos3reader {
        @Provenance { source = "nanos3reader@ff28f0b:README.md"; maturity = "verified"; }

        part factory : S3MinStreamFactory;

        // satisfy <RequirementDef> by <part that implements it>
        satisfy SeekableStream by factory.stream;
        satisfy RangeGet by factory.buf;
        satisfy ReadAhead by factory.buf;
        satisfy KeepAlivePerObject by factory.buf;
        satisfy SigV4Signing by factory.crypto;
        satisfy CredentialChain by factory.creds;
        satisfy RefreshTemporaryCredentials by factory.creds;
        satisfy SelfExplainingCredentialFailure by factory.creds;
        satisfy S3CompatibleStores by factory.config;
        satisfy WrongRegionRedirect by factory.buf;
        satisfy RetryWithBackoff by factory.buf;
        satisfy MinimalDependencies by factory.crypto;
        satisfy SelectableCryptoBackend by factory.crypto;
        satisfy SmallStaticBuild by factory.tls;
        satisfy ReadOnlyByDesign by factory;
    }
}
