A person (or your ops team) manually adds the new credentials into Secrets Manager using a staging label.
No full rotation Lambda is needed — this is lightweight and works great for API keys, tokens, OAuth creds, etc.
Recommended staging label: AWSPENDING (AWS standard)
AWS designed the label AWSPENDING exactly for "the next version that will become current".
You can use your custom AWSNEXT if you prefer (it works the same), but AWSPENDING is the convention used in all AWS documentation, examples, and rotation templates.
1. How the person manually adds the next credentials
Via AWS Console (easiest for a person):

Go to Secrets Manager → your secret → Retrieve secret value tab.
Click Edit (or Create new version / Update secret value).
Paste your new JSON in the Secret value field.
In Version staging labels:
Do NOT select AWSCURRENT.
Select Custom staging label → type exactly AWSPENDING (or AWSNEXT if you want to keep your old label).

Click Save.

→ New version is created with only AWSPENDING.
Current apps continue using the old AWSCURRENT. No disruption.