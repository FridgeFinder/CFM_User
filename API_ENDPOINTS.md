# User Service API Endpoints

## 1. Create User
**POST** `/v1/users`
- **Auth**: Required (Firebase JWT)
- **Description**: Create a new user account. Users are automatically assigned the `Neighbor` type.

**Request Body:**
```json
{
  "userId": "firebase-uid-here",
  "username": "mariamekaba",
  "email": "mariame@example.com",
  "phoneNumber": "+1234567890",
  "zipcode": "12345",
  "settings": {
    "emailNotificationEnabled": true,
    "geofenceEnabled": false
  }
}
```

**Success Response (201 Created):**
```json
{
  "user": {
    "userId": "firebase-uid-here",
    "userType": "Neighbor",
    "username": "mariamekaba",
    "email": "mariame@example.com",
    "phoneNumber": "1234567890",
    "zipcode": "12345",
    "points": 0,
    "settings": {
      "emailNotificationEnabled": true,
      "geofenceEnabled": false
    },
    "createdAt": "2024-03-20T14:22:00.000Z",
    "lastUpdated": "2024-03-20T14:22:00.000Z",
    "lastLoginAt": "2024-03-20T14:22:00.000Z"
  }
}
```

---

## 2. Get User
**GET** `/v1/users/{userId}`
- **Auth**: Required (Firebase JWT)
- **Description**: Retrieve user profile. Users can only access their own profile.

**Success Response (200 OK):**
```json
{
  "user": {
    "userId": "firebase-uid-here",
    "userType": "Neighbor",
    "username": "mariamekaba",
    "email": "mariame@example.com",
    "phoneNumber": "1234567890",
    "zipcode": "12345",
    "points": 0,
    "settings": {
      "emailNotificationEnabled": true,
      "geofenceEnabled": false
    },
    "createdAt": "2024-03-20T14:22:00.000Z",
    "lastUpdated": "2024-03-20T14:22:00.000Z",
    "lastLoginAt": "2024-03-20T14:22:00.000Z"
  }
}
```

---

## 3. Update User
**PATCH** `/v1/users/{userId}`
- **Auth**: Required (Firebase JWT)
- **Description**: Partially update user profile. Only provided fields are updated.

**Request Body (example):**
```json
{
  "email": "newemail@example.com",
  "settings": {
    "geofenceEnabled": true
  }
}
```

**Success Response (200 OK):**
```json
{
  "user": {
    "userId": "firebase-uid-here",
    "userType": "Neighbor",
    "username": "mariamekaba",
    "email": "newemail@example.com",
    "phoneNumber": "1234567890",
    "zipcode": "12345",
    "points": 0,
    "settings": {
      "emailNotificationEnabled": true,
      "geofenceEnabled": false
    },
    "createdAt": "2024-03-20T14:22:00.000Z",
    "lastUpdated": "2024-03-20T15:30:00.000Z",
    "lastLoginAt": "2024-03-20T14:22:00.000Z"
  }
}
```

---

## 4. Delete User
**DELETE** `/v1/users/{userId}`
- **Auth**: Required (Firebase JWT)
- **Description**: Permanently delete user account. Users can only delete their own account.

**Success Response (204 No Content):**
```
(Empty response body)
```

---

## 5. Check Username Availability
**GET** `/v1/users/check-username/{username}`
- **Auth**: Not required (Public endpoint)
- **Description**: Check if a username is available.

**Success Response (200 OK):**
```json
{
  "available": true
}
```

---

## 6. Username Suggestions
**GET** `/users/username-suggestions?count=NUMBER`
- **Auth**: Not required (Public endpoint)
- **Description**: Generate unique username suggestions that are validated against the users table.
- **Query Params**:
  - `count` (optional): Number of suggestions to return, integer between `1` and `20` (default: `1`).

**Success Response (200 OK):**
```json
{
  "suggestions": [
    "ActiveApple-1234",
    "BraveBerry-8891"
  ],
  "count": 2
}
```

---

## 7. Register or Update Push Device
**POST** `/v1/users/{userId}/user-devices/{installationId}`
- **Auth**: Required (Firebase JWT)
- **Description**: Register a device token or update the token for an existing installation.

**Request Body:**
```json
{
  "token": "fcm-token-here",
  "platform": "ios"
}
```

**Success Response (204 No Content):**
```
(Empty response body)
```

---

## 8. Unregister Push Device
**DELETE** `/v1/users/{userId}/user-devices/{installationId}`
- **Auth**: Required (Firebase JWT)
- **Description**: Remove one device registration for the authenticated user.

**Success Response (204 No Content):**
```
(Empty response body)
```

---

## API Base URLs
- **Development**: `https://users-api-dev.communityfridgefinder.com`
- **Staging**: `https://users-api-staging.communityfridgefinder.com`
- **Production**: `https://users-api-prod.communityfridgefinder.com`
- **Local**: `http://localhost:3000`

## Authentication
All endpoints (except username availability) require Firebase JWT in the `Authorization` header:
```
Authorization: Bearer <your-firebase-jwt-token>
```

## User Types
- **Organizer**: Coordinates the fridge network
- **Host**: Hosts a fridge at their location
- **Volunteer**: Maintains, fills, and cleans fridges
- **Neighbor**: Uses the community fridges (default for new users)

## Documentation
Interactive docs: https://fridgefinder.github.io/CFM_User/
