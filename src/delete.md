Request comes in
    ↓
Check cache → Token valid? → YES → Use it ✓
    ↓ NO
Get AWSCURRENT credentials
    ↓
Call OAuth provider → Success? → YES → Cache + return ✓
    ↓ NO (401 error)
Get AWSPENDING credentials
    ↓
Call OAuth provider → Success? → YES → Promote AWSPENDING to AWSCURRENT
    ↓                                     Cache + return ✓
    NO
    ↓
FAIL (both credentials bad) ✗