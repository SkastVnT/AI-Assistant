# ⚠️ Security Notice

## Environment Variables

The `.env` file contains sensitive information:
- API keys (ImgBB, etc.)
- Database credentials
- OAuth tokens
- Other secrets

## Important:
1. ✅ `.env` is in `.gitignore` - **DO NOT commit it to git!**
2. ✅ Use `.env.example` as template
3. ✅ Keep your API keys private
4. ✅ Rotate keys if accidentally exposed

## Setup:
```bash
# Copy example file
cp .env.example .env

# Edit with your actual keys
notepad .env  # Windows
nano .env     # Linux/Mac
```

## Current .env contents (example):
```env
IMGBB_API_KEY=your_api_key_here
```

## If .env is accidentally committed:
1. Delete from git history:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   ```

2. Rotate all exposed keys immediately!

3. Push force:
   ```bash
   git push origin --force --all
   ```
