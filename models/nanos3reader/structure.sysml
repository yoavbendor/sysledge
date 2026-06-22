package Nanos3readerStructure {
    doc /*
     * Physical/logical structure of nanos3reader, extracted from include/nanos3reader/s3_reader.h
     * and src/s3_reader.cpp at nanos3reader@ff28f0b. Parts mirror the real C++ types; the crypto
     * and TLS backends are modeled as variation points because they are genuine build-time variants.
     */
    import Concepts::*;
    import ScalarValues::*;

    // --- Build-time variant backends ---------------------------------------------------
    // SigV4 needs only SHA-256; the backend is chosen at configure time. Modeled as a
    // variation so the "common part, two variants" pattern is explicit and reusable.
    part def Sha256Backend {
        doc /* Provides SHA-256 (and HMAC-SHA256 built generically on it) for SigV4. */
    }
    part def OpenSslSha256 :> Sha256Backend {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#sha256_raw"; maturity = "verified"; }
        doc /* Default: SHA-256 from OpenSSL libcrypto. */
    }
    part def BundledSha256 :> Sha256Backend {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#Sha256"; maturity = "verified"; }
        doc /* In-tree compact SHA-256 (FIPS 180-4); links no crypto library. */
    }

    // The TLS backend libcurl is built against — also a deployment variant (affects binary size).
    part def TlsBackend;
    part def OpenSslTls :> TlsBackend {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#small-static-builds-mbedtls"; maturity = "verified"; }
    }
    part def MbedTlsTls :> TlsBackend {
        @Provenance { source = "nanos3reader@ff28f0b:README.md#small-static-builds-mbedtls"; maturity = "designed"; }
    }

    // --- Internal components -----------------------------------------------------------

    part def Config {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#Config"; maturity = "implemented"; }
        doc /* Resolved-once S3 configuration. */
        attribute region : String;
        attribute endpoint : String;       // empty -> virtual-hosted; set -> path-style
        attribute pathStyle : Boolean;
        attribute maxAttempts : Integer;    // AWS_MAX_ATTEMPTS, >= 1
    }

    part def CredentialProvider {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#CredentialProvider"; maturity = "implemented"; }
        doc /* Thread-safe provider walking the credential chain, caching + refreshing temporaries. */
        port credSource : CredentialSourcePort;
    }

    part def S3Streambuf {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#S3Streambuf"; maturity = "implemented"; }
        doc /* Seekable std::streambuf over S3 range GETs; owns one reused libcurl handle and one window. */
        attribute readAhead : Integer;
        attribute windowStart : Integer;
        attribute windowLen : Integer;
        attribute reachedEof : Boolean;
        port http : ByteRangeReadPort;       // outbound: HTTP(S) range GETs to the store
    }

    part def S3IStream {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#S3IStream"; maturity = "implemented"; }
        doc /* std::istream owning its S3Streambuf, returned to the caller. */
        port reads : ByteRangeReadPort;       // inbound: caller's seekg/read
    }

    // --- Top-level assembly ------------------------------------------------------------

    part def S3MinStreamFactory {
        @Provenance { source = "nanos3reader@ff28f0b:include/nanos3reader/s3_reader.h#S3MinStreamFactory"; maturity = "verified"; }
        doc /* Process-singleton factory: resolves Config once and opens S3 objects as seekable istreams. */

        part config : Config;
        part creds : CredentialProvider;

        // Each open() produces a streambuf wrapped in an istream.
        part buf : S3Streambuf;
        part stream : S3IStream;

        // Backend variation points (resolved per build, not per object).
        variation part crypto : Sha256Backend {
            variant part openssl : OpenSslSha256;   // default
            variant part bundled : BundledSha256;   // small-static builds
        }
        variation part tls : TlsBackend {
            variant part openssl : OpenSslTls;
            variant part mbedtls : MbedTlsTls;
        }

        // Realized stream interface the caller consumes.
        interface caller : ByteRangeReadStream connect supplier to stream.reads;

        // Internal wiring: the istream delegates range fetches to the streambuf's HTTP port.
        connect stream.reads to buf.http;
    }
}
