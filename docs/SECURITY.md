# Security Notes

## Service account credentials

The Google Sheets service-account key (`credentials/gsheets_key.json`) is a
**sensitive credential**. It is git-ignored, but it must still be treated as
a secret.

### Rules

1. **Never commit** `credentials/gsheets_key.json` to source control.
   The `.gitignore` already excludes the `credentials/` folder, plus
   `credentials/*.json` as a defensive belt-and-braces rule.
2. **Never paste** the private key into chat, issues, or PRs.
3. **Rotate immediately** if you suspect the key has leaked.

### Rotation procedure (if the key has been exposed)

1. Go to <https://console.cloud.google.com/iam-admin/serviceaccounts>.
2. Open the service account (e.g. `hospital-py-api@…`).
3. **Keys** tab → click the leaked key → **Delete**.
4. **Add Key → Create new key → JSON**. A new file downloads.
5. Replace `credentials/gsheets_key.json` with the new file **on your local
   machine only**. Do not push it anywhere.
6. Re-share any Google Sheet that the old key was given access to with the
   new `client_email`.

### Template

A redacted template lives at `credentials/gsheets_key.json.example`. Copy it
to `credentials/gsheets_key.json` and fill in the real values:

```bash
cp credentials/gsheets_key.json.example credentials/gsheets_key.json
# then edit credentials/gsheets_key.json with your real key
```

## Spreadsheet ID

`SPREADSHEET_ID` is a runtime secret. Set it via the `.env` file (already
in `.gitignore`) or your environment, never hard-code it in a script. The
pipeline will skip the Google Sheets step gracefully if the env var is
missing.
