"""Constants for the Kwatt integration."""

DOMAIN = "kwatt"
CONF_CIC = "cic"

# API URLs
FIREBASE_INSTALLATIONS_URL = "https://firebaseinstallations.googleapis.com/v1/projects/quatt-production/installations"
FIREBASE_SIGNUP_URL = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser"
FIREBASE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
QUATT_API_BASE_URL = "https://mobile-api.quatt.io/api/v1"

# Firebase configuration (from Postman environment)
GOOGLE_API_KEY = "AIzaSyDM4PIXYDS9x53WUj-tDjOVAb6xKgzxX9Y"
GOOGLE_ANDROID_PACKAGE = "io.quatt.mobile.android"
GOOGLE_ANDROID_CERT = "1110A8F9B0DE16D417086A4BDBCF956070F0FD97"
GOOGLE_FIREBASE_CLIENT = "H4sIAAAAAAAAAKtWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA"
GOOGLE_APP_ID = "1:1074628551428:android:20ddeaf85c3cfec3336651"
GOOGLE_APP_INSTANCE_ID = "dwNCvvXLQrqvmUJlZajYzG"

# Update intervals
UPDATE_INTERVAL = 300  # 5 minutes

# Storage keys
STORAGE_KEY = "kwatt_storage"
STORAGE_VERSION = 1
