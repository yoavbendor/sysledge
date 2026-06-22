# Requirements Table

| # | Requirement | Kind | File | Line | Doc | Members |
|---|-------------|------|------|------|-----|---------|
| 0 | CredentialChain | requirement_definition | requirements.sysml | 53 | Resolve credentials: env -&gt; shared profile files (incl credential_process) -&gt; ECS/EKS -&gt; EC2 IMDSv2. | 2 |
| 1 | KeepAlivePerObject | requirement_definition | requirements.sysml | 35 | One libcurl handle is reused across windows so the connection stays keep-alive per object. | 2 |
| 2 | MinimalDependencies | requirement_definition | requirements.sysml | 105 | Depend only on libcurl + a small SHA-256 — no AWS SDK. | 2 |
| 3 | RangeGet | requirement_definition | requirements.sysml | 19 | Reads are served by HTTP(S) Range GETs (bytes&#x3D;start-last), never whole-object fetches. | 2 |
| 4 | ReadAhead | requirement_definition | requirements.sysml | 27 | Each GET pulls a read-ahead window; slices within a window cost no extra GET. | 2 |
| 5 | ReadOnlyByDesign | requirement_definition | requirements.sysml | 131 | Read/GET-only: no PUT, no multipart, no LIST, no SSO/assume-role resolution. | 2 |
| 6 | RefreshTemporaryCredentials | requirement_definition | requirements.sysml | 61 | Temporary credentials are refreshed a few minutes before they expire. | 2 |
| 7 | RetryWithBackoff | requirement_definition | requirements.sysml | 95 | Transient transport/5xx/429 failures retry with full-jitter exponential backoff; AWS_MAX_ATTEMPTS tunes it. | 2 |
| 8 | S3CompatibleStores | requirement_definition | requirements.sysml | 79 | AWS_ENDPOINT_URL selects path-style addressing for MinIO/R2/other S3-compatible stores. | 2 |
| 9 | SeekableStream | requirement_definition | requirements.sysml | 11 | Open an s3://bucket/key object as a seekable, read-ahead-buffered std::istream. | 2 |
| 10 | SelectableCryptoBackend | requirement_definition | requirements.sysml | 113 | SHA-256 backend is chosen at build time (OpenSSL or bundled) with byte-identical signatures. | 2 |
| 11 | SelfExplainingCredentialFailure | requirement_definition | requirements.sysml | 69 | On failure, the error names every credential source tried and why each yielded nothing. | 2 |
| 12 | SigV4Signing | requirement_definition | requirements.sysml | 45 | Requests are signed with AWS Signature Version 4, validated against AWS test vectors. | 2 |
| 13 | SmallStaticBuild | requirement_definition | requirements.sysml | 121 | Support a small self-contained static binary (~2.2 MB with mbedTLS curl + bundled SHA-256). | 2 |
| 14 | WrongRegionRedirect | requirement_definition | requirements.sysml | 87 | A wrong-region response is retargeted once using the x-amz-bucket-region header. | 2 |

**Total**: 15 requirements
