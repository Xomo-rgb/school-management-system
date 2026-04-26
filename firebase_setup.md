# Firebase Setup Instructions

## Step 1: Create Firebase Project
1. Go to https://console.firebase.google.com/
2. Click "Add project"
3. Name it "harmony-school-system" (or your choice)
4. Disable Google Analytics (optional)
5. Click "Create project"

## Step 2: Enable Firestore Database
1. In Firebase Console, click "Firestore Database"
2. Click "Create database"
3. Choose "Start in production mode"
4. Select your region (choose closest to your users)
5. Click "Enable"

## Step 3: Get Service Account Key
1. Go to Project Settings (gear icon) > Service accounts
2. Click "Generate new private key"
3. Save the JSON file as `firebase-credentials.json`
4. Move it to your project root: `Harmony Project/firebase-credentials.json`
5. **IMPORTANT**: Add to .gitignore to keep it secret!

## Step 4: Install Firebase Admin SDK
Run in terminal:
```bash
pip install firebase-admin
```

## Step 5: Update .gitignore
Add this line:
```
firebase-credentials.json
```

## Next Steps
After completing these steps, I'll update your code to use Firebase!
