package Nanos3readerBehavior {
    doc /*
     * Behavior of nanos3reader's read path, extracted from src/s3_reader.cpp at nanos3reader@ff28f0b.
     * Actions mirror the real control flow so agents can reason about it without re-reading the C++.
     */
    import Concepts::*;

    action def ResolveCredentials {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#CredentialProvider::resolve"; maturity = "implemented"; }
        doc /*
         * Walk the chain in order, returning the first source that yields usable keys:
         *   1. env (AWS_ACCESS_KEY_ID/SECRET/SESSION_TOKEN)
         *   2. shared profile files, then the profile's credential_process helper
         *   3. ECS/EKS container endpoint (AWS_CONTAINER_CREDENTIALS_*)
         *   4. EC2 instance role via IMDSv2 (falls back to IMDSv1)
         * On total failure, accumulate a per-source diagnostic for error().
         */
        out item credentials;     // access key, secret, optional session token + expiry
        out item diagnostic;      // "source: reason" chain when nothing resolved
    }

    action def BuildAuthorization {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#build_authorization"; maturity = "verified"; }
        doc /* Construct the canonical request, string-to-sign, signing key, and Authorization header (SigV4). */
        in item canonicalRequest;
        in item credentials;
        out item authorizationHeader;
    }

    action def LoadWindow {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#load_window"; maturity = "implemented"; }
        doc /*
         * Fetch [start, start+readAhead-1] into the window:
         *   - sign + issue a Range GET on the reused curl handle (keep-alive)
         *   - 200/206 -> install window; 416 -> empty window at EOF
         *   - wrong-region (301/307/400 + x-amz-bucket-region) -> retarget once, retry free
         *   - transient transport / 5xx / 429 -> full-jitter backoff, up to maxAttempts
         *   - otherwise -> fail() sets the thread-local last error
         */
        in item start;
        in item credentials;
        out item window;
        out item reachedEof;
    }

    action def Seek {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#seekpos"; maturity = "implemented"; }
        doc /* Move the get pointer; if the target is inside the live window, reposition with no GET, else LoadWindow. */
        in item target;
        out item position;
    }

    action def OpenStream {
        @Provenance { source = "nanos3reader@ff28f0b:src/s3_reader.cpp#S3MinStreamFactory::open"; maturity = "verified"; }
        doc /*
         * Parse s3://bucket/key, verify credentials resolve, construct an S3Streambuf wrapped in an
         * S3IStream. Returns nullptr (with error() set) on a bad URI or missing credentials.
         */
        in item uri;
        in item readAheadBytes;
        out item stream;

        // Decomposition: opening first resolves credentials, then subsequent reads load windows.
        action resolve : ResolveCredentials;
        action firstLoad : LoadWindow;
    }
}
