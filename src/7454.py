To run this "Sira Portal" rotation manually using the AWS CLI, you need to follow the three distinct phases of your design: Manual Upload, Manual Verification, and Automatic (or Manual) Promotion.

Phase 1: Manual Upload (Sira's Role)
Someone (a manager or a script) creates a new version of the secret but does not make it live yet. They attach the AWSNEXT label to it.

Bash
aws secretsmanager put-secret-value \
    --secret-id MySecretName \
    --secret-string '{"client_id":"939393_NEW","client_secret":"NEW_PASSWORD_XYZ"}' \
    --version-stages AWSNEXT
Result: You now have a "waiting room" version. AWSCURRENT still points to the old working credentials.

Phase 2: Manual Verification (The "Test")
Before you promote it, you should verify that the AWSNEXT version actually works. You can pull specifically that version using the staging label.

Bash
aws secretsmanager get-secret-value \
    --secret-id MySecretName \
    --version-stage AWSNEXT
Action: Take these credentials and try a manual curl login. If it fails, do not proceed to Phase 3.

Phase 3: Promotion (The Failover)
This is what your Lambda does automatically, but you can trigger it via CLI if you need to force a rotation. You must move the AWSCURRENT label to the new version ID.

1. Find the Version IDs
First, look at the secret to see which ID has which label:

Bash
aws secretsmanager describe-secret --secret-id MySecretName --query 'VersionIdsToStages'
2. Perform the Swap
Assuming Version-New-ID has the AWSNEXT label and Version-Old-ID has the AWSCURRENT label:

Bash
aws secretsmanager update-secret-version-stage \
    --secret-id MySecretName \
    --version-stage AWSCURRENT \
    --move-to-version-id <Version-New-ID> \
    --remove-from-version-id <Version-Old-ID>
Behind the scenes: AWS will now move AWSCURRENT to the new version and automatically move AWSPREVIOUS to the old version.

3. Cleanup the Custom Label
Finally, remove the AWSNEXT label so the system is ready for the next manual update:

Bash
aws secretsmanager update-secret-version-stage \
    --secret-id MySecretName \
    --version-stage AWSNEXT \
    --remove-from-version-id <Version-New-ID>
Phase 4: Toggle the Parameter Store (Optional)
If you are using the Parameter Store "Traffic Cop" design, don't forget to update the toggle so your apps know to look at the new version.

Bash
aws ssm put-parameter \
    --name "/auth/app/active_version" \
    --value "AWSCURRENT" \
    --type String \
    --overwrite
Quick Troubleshooting Command
If you ever get confused about which version is where, run this to see a clear list of all versions and their post-it note labels:

Bash
aws secretsmanager list-secret-version-ids --secret-id MySecretName