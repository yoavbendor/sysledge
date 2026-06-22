package Nanos3readerRequirements {
    doc /*
     * Requirements for nanos3reader — a minimal, read-only S3 range reader for C++.
     * Extracted from the repository at nanos3reader@ff28f0b (README.md, headers, sources).
     * Every requirement carries @Provenance naming the source it was read from.
     */
    import Concepts::*;
    import ScalarValues::*;

    // --- Functional: the core reading contract ----------------------------------------

    requirement def <'R-1'> SeekableStream {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#why"; maturity = "verified"; }
        doc /* Open an s3://bucket/key object as a seekable, read-ahead-buffered std::istream. */
        attribute id : String = "R-1";
        attribute text : String =
            "The reader shall expose an S3 object as a seekable std::istream supporting seekg/read.";
    }

    requirement def <'R-2'> RangeGet {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#load_window"; maturity = "verified"; }
        doc /* Reads are served by HTTP(S) Range GETs (bytes=start-last), never whole-object fetches. */
        attribute id : String = "R-2";
        attribute text : String =
            "Each window load shall fetch its bytes via an HTTP Range GET handling 200/206/416 responses.";
    }

    requirement def <'R-3'> ReadAhead {
        @Provenance { source = "nanos3reader@ff28f0b:include/nanos3reader/s3_reader.h#open"; maturity = "verified"; }
        doc /* Each GET pulls a read-ahead window; slices within a window cost no extra GET. */
        attribute id : String = "R-3";
        attribute text : String =
            "The reader shall fetch read_ahead_bytes per GET so consecutive in-window reads issue no new GET.";
    }

    requirement def <'R-4'> KeepAlivePerObject {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#S3Streambuf"; maturity = "implemented"; }
        doc /* One libcurl handle is reused across windows so the connection stays keep-alive per object. */
        attribute id : String = "R-4";
        attribute text : String =
            "The reader shall reuse one keep-alive connection per opened object across window refetches.";
    }

    // --- Functional: signing and credentials ------------------------------------------

    requirement def <'R-5'> SigV4Signing {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#features"; maturity = "verified"; }
        doc /* Requests are signed with AWS Signature Version 4, validated against AWS test vectors. */
        attribute id : String = "R-5";
        attribute text : String =
            "The reader shall sign requests with AWS SigV4, matching AWS's published known-answer vectors.";
    }

    requirement def <'R-6'> CredentialChain {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#CredentialProvider"; maturity = "implemented"; }
        doc /* Resolve credentials: env -> shared profile files (incl credential_process) -> ECS/EKS -> EC2 IMDSv2. */
        attribute id : String = "R-6";
        attribute text : String =
            "Credentials shall resolve via env, then shared profiles (incl credential_process), then ECS, then IMDSv2.";
    }

    requirement def <'R-7'> RefreshTemporaryCredentials {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#CredentialProvider"; maturity = "implemented"; }
        doc /* Temporary credentials are refreshed a few minutes before they expire. */
        attribute id : String = "R-7";
        attribute text : String =
            "Temporary credentials shall be refreshed before expiry (with a safety margin) and cached otherwise.";
    }

    requirement def <'R-8'> SelfExplainingCredentialFailure {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#describe_profile_gap"; maturity = "implemented"; }
        doc /* On failure, the error names every credential source tried and why each yielded nothing. */
        attribute id : String = "R-8";
        attribute text : String =
            "When no credentials are found, error() shall name each source attempted and the reason it failed.";
    }

    // --- Functional: robustness and compatibility -------------------------------------

    requirement def <'R-9'> S3CompatibleStores {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#configuration-environment"; maturity = "verified"; }
        doc /* AWS_ENDPOINT_URL selects path-style addressing for MinIO/R2/other S3-compatible stores. */
        attribute id : String = "R-9";
        attribute text : String =
            "Setting AWS_ENDPOINT_URL shall switch to path-style addressing against the given endpoint.";
    }

    requirement def <'R-10'> WrongRegionRedirect {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#load_window"; maturity = "implemented"; }
        doc /* A wrong-region response is retargeted once using the x-amz-bucket-region header. */
        attribute id : String = "R-10";
        attribute text : String =
            "On a wrong-region redirect the reader shall retarget to x-amz-bucket-region once and retry.";
    }

    requirement def <'R-11'> RetryWithBackoff {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#configuration-environment"; maturity = "implemented"; }
        doc /* Transient transport/5xx/429 failures retry with full-jitter exponential backoff; AWS_MAX_ATTEMPTS tunes it. */
        attribute id : String = "R-11";
        attribute text : String =
            "Transient failures shall retry up to AWS_MAX_ATTEMPTS (default 3) with full-jitter exponential backoff.";
    }

    // --- Quality / build-time -----------------------------------------------------------

    requirement def <'R-12'> MinimalDependencies {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#why"; maturity = "verified"; }
        doc /* Depend only on libcurl + a small SHA-256 — no AWS SDK. */
        attribute id : String = "R-12";
        attribute text : String =
            "The library shall depend only on libcurl and a SHA-256 source, with no AWS SDK dependency.";
    }

    requirement def <'R-13'> SelectableCryptoBackend {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#sigv4-crypto-backend"; maturity = "verified"; }
        doc /* SHA-256 backend is chosen at build time (OpenSSL or bundled) with byte-identical signatures. */
        attribute id : String = "R-13";
        attribute text : String =
            "The SHA-256 backend shall be selectable (openssl|bundled) and produce byte-identical signatures.";
    }

    requirement def <'R-14'> SmallStaticBuild {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#small-static-builds-mbedtls"; maturity = "designed"; }
        doc /* Support a small self-contained static binary (~2.2 MB with mbedTLS curl + bundled SHA-256). */
        attribute id : String = "R-14";
        attribute text : String =
            "The library shall support a small static build (~2.2 MB s3cat) via mbedTLS curl + bundled SHA-256.";
    }

    // --- Constraints / non-goals (explicit scope boundaries) --------------------------

    requirement def <'R-15'> ReadOnlyByDesign {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#scope--non-goals"; maturity = "verified"; }
        doc /* Read/GET-only: no PUT, no multipart, no LIST, no SSO/assume-role resolution. */
        attribute id : String = "R-15";
        attribute text : String =
            "The reader shall be read/GET-only: no PUT, multipart, LIST, or SSO/assume-role credential resolution.";
    }
}
