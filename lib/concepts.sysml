package Concepts {
    doc /*
     * Shared modeling vocabulary for the sysledge knowledge base.
     *
     * Every system model (nanos3reader today; nanotins/nanolance/nanoarrow2parquet and
     * future hardware systems later) imports this package so facts are recorded the same
     * way everywhere. Keeping it small and stable is deliberate — see docs/conventions.md.
     */
    import ScalarValues::*;

    // --- Provenance -------------------------------------------------------------------
    // The anti-guessing mechanism. Every element that ASSERTS A FACT about a real system
    // must carry a @Provenance pointing at the raw source it was extracted from. An element
    // with no provenance is a hypothesis (maturity = "concept") and is reported by lint.
    metadata def Provenance {
        // Where the fact came from: "<repo>@<commit>:<path>[#anchor]" or a raw/ source-id.
        attribute source : String;
        // Lifecycle stage of the modeled thing: concept | designed | implemented | verified.
        attribute maturity : String;
    }

    // --- Reusable interfaces shared across systems ------------------------------------

    // A read-only, seekable byte-range stream over some backing store. nanos3reader realizes
    // it over S3; other systems may realize the same shape over files, HTTP, etc. This is the
    // kind of "common/near-equal concept" the knowledge base is meant to factor out.
    port def ByteRangeReadPort {
        doc /* Pull a byte range [offset, offset+length) and seek within the object. */
    }

    interface def ByteRangeReadStream {
        doc /* Consumer reads ranges; supplier serves them from a backing store. */
        end port consumer : ByteRangeReadPort;
        end port supplier : ByteRangeReadPort;
    }

    // A source of AWS-style credentials (env, shared profile, container, instance role).
    // Reused by any system in the family that talks to AWS / S3-compatible services.
    port def CredentialSourcePort {
        doc /* Yields access key, secret key, optional session token + expiry. */
    }
}
