Test 1 — L1 Cache Hit
The token already exists in the in-memory cache from a previous call. The rotator must return it immediately without making any calls to Secrets Manager or the OAuth server. Validates that the fastest path works correctly and no unnecessary network calls are made.

Test 2 — L2 Cache Hit (Secrets Manager)
No token exists in memory, but a valid JWT is stored inside Secrets Manager. The rotator must retrieve it, skip OAuth entirely, and populate the in-memory cache for future calls. Confirms the second-tier cache layer works as a fallback before reaching the OAuth server.

Test 3 — Normal OAuth Flow
Both caches are empty, so the rotator must call OAuth using the current AWSCURRENT credentials and receive a fresh token. The token must then be stored in both L1 and L2. Validates the standard happy-path acquisition works end to end.

Test 4 — AWSCURRENT Fails, AWSPENDING Succeeds
The AWSCURRENT credentials are rejected with a 401, triggering the rotation logic. The rotator must fall back to AWSPENDING credentials, acquire a token successfully, and promote AWSPENDING to become the new AWSCURRENT. Validates the core rotation flow works correctly under a credential failure.

Test 5 — Rotation with No AWSPENDING Available
AWSCURRENT credentials fail but no AWSPENDING secret has been configured in Secrets Manager. The rotator must raise a meaningful exception rather than silently failing or entering an infinite loop. Confirms the system fails loudly and clearly when rotation is not set up.

Test 6 — Both AWSCURRENT and AWSPENDING Fail
Both credential sets are invalid and OAuth rejects all acquisition attempts. The rotator must raise an informative exception that clearly identifies both credential stages failed. Ensures no partial side effects such as promotion or token storage occur in a total failure scenario.

Test 7 — Network Error Does Not Trigger Rotation
A non-authentication error such as a connection timeout occurs during OAuth. The rotator must re-raise it immediately without attempting rotation, since the failure is infrastructure-related, not credential-related. Prevents false rotations that would corrupt a perfectly valid secret.

Test 8 — Token Stored in Both Caches After Rotation
After a successful rotation, the new token must be written to both the in-memory L1 cache and Secrets Manager L2 cache. Validates the correct token value, expiry, and stage are persisted. Ensures subsequent calls are served from cache rather than triggering OAuth again.

Test 9 — Expired L1 Cache Falls Through to OAuth
An expired token is present in the in-memory cache, but TokenCache.get() correctly returns None for it. The rotator must detect this, bypass the stale entry, and proceed to acquire a fresh token via OAuth. Validates that expiry logic in the cache layer is respected by the rotator.

Test 10 — OAuth Called with Correct Credentials
Confirms the exact OAuthCredentials object retrieved from AWSCURRENT is passed directly to acquire_token. Prevents subtle bugs where the wrong credentials object, a mock, or stale data could be forwarded. Validates the wiring between the secrets layer and the OAuth layer is precise.

Test 11 — Promote Never Called on Successful Flow
When AWSCURRENT credentials work without issue, the rotator must never call get_pending_credentials or promote_pending_to_current. Validates that the rotation path is completely isolated from the happy path. Prevents accidental version promotions that would silently overwrite a working secret.

Test 12 — store_jwt Always Uses AWSCURRENT Stage
After any successful token acquisition, the JWT must be persisted back to Secrets Manager using the AWSCURRENT stage, never any other. Validates the stage argument is hardcoded correctly and cannot drift. Acts as a regression guard against accidental writes to the wrong secret version.

Test 13 — L1 Cache Populated After Normal Flow
After the first successful OAuth call, the token must be stored in L1 so that the second call is served entirely from memory. Confirms acquire_token is called exactly once across two consecutive invocations. Validates the caching contract that protects the OAuth server from repeated requests.

Test 14 — AWS ThrottlingException Does Not Trigger Rotation
A ThrottlingException from AWS is an infrastructure rate-limit error, not an authentication failure. The rotator must re-raise it without touching AWSPENDING credentials or attempting promotion. Prevents the system from corrupting a valid secret simply because AWS was temporarily rate-limiting requests.

Test 15 — Rotation Uses Pending Credentials, Not Current
During rotation, the first OAuth call must use AWSCURRENT credentials and the second must use AWSPENDING credentials in that exact order. Validates the call sequence and argument correctness using call_args_list. Prevents a bug where both calls accidentally use the same failing credentials.

Test 16 — store_jwt Expires At Matches Token
The expires_at value written to Secrets Manager must exactly match the value returned by token.expires_at_unix() and must be a positive future timestamp. Validates there is no off-by-one error or unit mismatch between the token model and what is persisted. Ensures cache invalidation timing is consistent across both cache layers.

Test 17 — Non-Auth ClientError Bubbles Up
A ClientError with a non-authentication code such as InternalServerError must be re-raised immediately without triggering rotation. Validates that the if error_code in {...} guard correctly distinguishes infrastructure errors from credential errors. Confirms line 62 is reachable and the raise path works correctly.

Test 18 — Auth ClientError Codes Trigger Rotation
A ClientError carrying either UnauthorizedException or AccessDeniedException must be treated as a credential failure and trigger the AWSPENDING rotation flow. Parametrized to cover both codes in a single test. Validates the error_code branch guard correctly routes auth failures into rotation.

Test 19 — BadCredentialsError Caught by ClientError Block
Since BadCredentialsError is a subclass of ClientError, it must be caught by the except ClientError block and route correctly into rotation. Validates the exception inheritance hierarchy is wired in the right order. Confirms that the except block ordering does not cause auth errors to be silently swallowed or misrouted.

Test 20 — Promote Fails Mid-Rotation, No Partial State
OAuth succeeds with AWSPENDING credentials but the subsequent call to promote_pending_to_current raises a ClientError. Neither the L1 cache nor Secrets Manager must be written to, leaving the system in a clean state. Prevents a dangerous partial rotation where a new token is cached against a secret version that was never officially promoted.

Test 21 — store_jwt Failure Leaves Token in L1 Only
OAuth succeeds and the token is written to L1 memory cache, but the subsequent store_jwt call to Secrets Manager throws an exception. The rotator must surface the error while L1 remains populated. Confirms that a Secrets Manager write failure does not silently succeed and that the next cold Lambda start will correctly re-acquire from OAuth rather than serving a ghost cache entry.

Test 22 — Sequential Calls Return Same Token from L1
Two consecutive calls to get_valid_token must return identical tokens, with OAuth and Secrets Manager each called exactly once across both invocations. Simulates repeated Lambda invocations within the same execution environment. Validates that L1 caching correctly short-circuits all downstream calls after the first acquisition.