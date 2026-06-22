package Nanos3readerVerification {
    doc /*
     * Verification cases for nanos3reader and the requirements each one verifies, extracted from the
     * test suite and CI at nanos3reader@ff28f0b. "verify" links let an agent see what is actually
     * proven by a test versus only asserted by code.
     */
    import Concepts::*;
    import Nanos3readerRequirements::*;

    // SigV4 known-answer test: pure computation, no network. The correctness gate for signing.
    verification def SigV4KnownAnswer {
        @Provenance { source = "nanos3reader@ff28f0b:tests/sigv4_test.cpp"; maturity = "verified"; }
        doc /* Checks sha256(""), derive_signing_key, and a get-vanilla Authorization against AWS vectors. */
        subject signer;
        objective { doc /* Signatures match AWS's published SigV4 test vectors exactly. */ }
    }
    verification sigv4KnownAnswer : SigV4KnownAnswer {
        verify SigV4Signing;
    }

    // MinIO end-to-end integration test: real range GETs against a live S3-compatible store (CI).
    verification def MinioIntegration {
        @Provenance { source = "nanos3reader@ff28f0b:tests/minio_integration_test.cpp"; maturity = "verified"; }
        doc /*
         * Exercises path-style addressing via AWS_ENDPOINT_URL, real range GETs, read-ahead window
         * refetches, seeking within and across windows, EOF, and error reporting on a missing key —
         * checked byte-for-byte against a local copy. Self-skips (exit 77) without IT env vars.
         */
        subject reader;
        objective { doc /* Bytes read over range GETs match the seeded object exactly, across seeks and EOF. */ }
    }
    verification minioIntegration : MinioIntegration {
        verify SeekableStream;
        verify RangeGet;
        verify ReadAhead;
        verify S3CompatibleStores;
    }

    // CI crypto matrix: builds both SHA-256 backends and runs the SigV4 test on each.
    verification def CryptoBackendParity {
        @Provenance { source = "nanos3reader@ff28f0b:.github/workflows/ci.yml#build-test"; maturity = "verified"; }
        doc /* openssl and bundled SHA-256 both pass the SigV4 known-answer test => byte-identical signatures. */
        subject backends;
        objective { doc /* Both crypto backends produce identical signatures (the SigV4 test passes on each). */ }
    }
    verification cryptoBackendParity : CryptoBackendParity {
        verify SelectableCryptoBackend;
    }
}
