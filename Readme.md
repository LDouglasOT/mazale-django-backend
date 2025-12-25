# Dating App API Documentation

## Base URL
```
http://your-domain.com/api/
```

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <your_token>
```

---

## Authentication Endpoints

### Register User
**POST** `/api/auth/register/`

**Request Body:**
```json
{
  "phone_number": "+256700000000",
  "email": "user@example.com",
  "password": "securepassword123",
  "confirm_password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe",
  "gender": "male",
  "day": "15",
  "month": "06",
  "year": "1995"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": { ... },
  "token": "eyJ0eXAiOiJKV1QiLCJh...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJh..."
}
```

### Login User
**POST** `/api/auth/login/`

**Request Body:**
```json
{
  "phone_number": "+256700000000",
  "password": "securepassword123"
}
```
OR
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user": { ... },
  "token": "eyJ0eXAiOiJKV1QiLCJh...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJh..."
}
```

### Logout User
**POST** `/api/auth/logout/`

**Headers:** Authorization: Bearer <token>

**Response:**
```json
{
  "message": "Logout successful"
}
```

### Refresh Token
**POST** `/api/auth/token/refresh/`

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJh..."
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJh..."
}
```

---

## User Endpoints

### Get Current User Profile
**GET** `/api/users/me/`

**Response:**
```json
{
  "id": 1,
  "phone_number": "+256700000000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  ...
}
```

### Update Profile
**PUT** `/api/users/update_profile/`

**Request Body:**
```json
{
  "first_name": "John",
  "about": "Love traveling and meeting new people",
  "user_interests": ["travel", "music", "sports"],
  "user_images": ["url1", "url2", "url3"]
}
```

### Discover Users
**GET** `/api/users/discover/`

Returns list of users to discover (excludes already liked users)

**Response:**
```json
[
  {
    "id": 2,
    "first_name": "Jane",
    "last_name": "Smith",
    "profile_pic": "url",
    "user_images": ["url1", "url2"],
    ...
  }
]
```

### Get User List
**GET** `/api/users/`

**Query Parameters:**
- `page`: Page number
- `search`: Search by name

### Get User Detail
**GET** `/api/users/{id}/`

---

## Profile Like Endpoints

### Like a Profile
**POST** `/api/profile-likes/`

**Request Body:**
```json
{
  "liked_user": 2,
  "superlike": false
}
```

**Response:**
```json
{
  "id": 1,
  "liker": 1,
  "liked_user": 2,
  "superlike": false,
  "is_match": true,
  "match": { ... }
}
```

### Get My Likes
**GET** `/api/profile-likes/`

Returns profiles you've liked

### Get Received Likes
**GET** `/api/profile-likes/received/`

Returns profiles that liked you

---

## Match Endpoints

### Get Matches
**GET** `/api/matches/`

**Response:**
```json
[
  {
    "id": 1,
    "user1": 1,
    "user2": 2,
    "user1_details": { ... },
    "user2_details": { ... },
    "seen_by_user1": false,
    "seen_by_user2": false,
    "created_at": "2024-01-15T10:30:00"
  }
]
```

### Mark Match as Seen
**POST** `/api/matches/{id}/mark_seen/`

---

## Conversation & Message Endpoints

### Create/Get Conversation
**POST** `/api/conversations/`

**Request Body:**
```json
{
  "participants": [2]
}
```

### Get Conversations
**GET** `/api/conversations/`

**Response:**
```json
[
  {
    "id": 1,
    "participants": [1, 2],
    "participants_details": [ ... ],
    "last_message": { ... },
    "unread_count": 3,
    "created_at": "2024-01-15T10:00:00"
  }
]
```

### Get Conversation Messages
**GET** `/api/messages/?conversation=1`

### Send Message
**POST** `/api/messages/`

**Request Body:**
```json
{
  "conversation": 1,
  "receiver": 2,
  "sms": "Hello, how are you?",
  "is_text": true
}
```

### Mark Message as Seen
**POST** `/api/messages/{id}/mark_seen/`

### Mark All Conversation Messages as Seen
**POST** `/api/messages/mark_conversation_seen/`

**Request Body:**
```json
{
  "conversation_id": 1
}
```

---

## Moment Endpoints

### Get Moments (Feed)
**GET** `/api/moments/`

**Query Parameters:**
- `user_id`: Filter by user
- `page`: Page number

### Create Moment
**POST** `/api/moments/`

**Request Body:**
```json
{
  "tagline": "Beautiful sunset at the beach",
  "hashtag": "#sunset",
  "images": ["url1", "url2", "url3"]
}
```

### Get Moment Detail
**GET** `/api/moments/{id}/`

### Like Moment
**POST** `/api/moments/{id}/like/`

### Unlike Moment
**POST** `/api/moments/{id}/unlike/`

### Delete Moment
**DELETE** `/api/moments/{id}/`

---

## Comment Endpoints

### Get Comments for Moment
**GET** `/api/comments/?moment_id=1`

### Create Comment
**POST** `/api/comments/`

**Request Body:**
```json
{
  "moment": 1,
  "text": "Great photo!",
  "image": "optional_url"
}
```

### Delete Comment
**DELETE** `/api/comments/{id}/`

---

## Gift Endpoints

### Get Available Gifts
**GET** `/api/gifts/`

**Response:**
```json
[
  {
    "id": 1,
    "name": "Rose",
    "image": "url",
    "value": 100
  }
]
```

### Get User's Gifts
**GET** `/api/user-gifts/`

### Purchase Gift
**POST** `/api/user-gifts/purchase/`

**Request Body:**
```json
{
  "gift_id": 1,
  "quantity": 5
}
```

---

## Transaction Endpoints

### Get Transactions
**GET** `/api/transactions/`

### Create Transaction
**POST** `/api/transactions/`

**Request Body:**
```json
{
  "amount": 10000,
  "reason": "Coin purchase",
  "quantity": 100,
  "transaction_reference": "TXN123456",
  "mno_transaction_reference": "MNO123456"
}
```

---

## Withdrawal Endpoints

### Get Withdrawals
**GET** `/api/withdrawals/`

### Request Withdrawal
**POST** `/api/withdrawals/`

**Request Body:**
```json
{
  "amount": 50000,
  "quantity": 500,
  "mobile_number": "+256700000000"
}
```

---

## Notification Endpoints

### Get Notifications
**GET** `/api/notifications/`

Returns user-specific and global notifications

### Mark Notification as Seen
**POST** `/api/notifications/{id}/mark_seen/`

### Mark All Notifications as Seen
**POST** `/api/notifications/mark_all_seen/`

---

## Error Responses

All endpoints may return these error responses:

**400 Bad Request:**
```json
{
  "field_name": ["Error message"]
}
```

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**404 Not Found:**
```json
{
  "detail": "Not found."
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error."
}
```

---

## Pagination

List endpoints support pagination with these query parameters:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)

**Response Format:**
```json
{
  "count": 100,
  "next": "http://api.example.com/api/users/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

---

## Filtering & Searching

Many list endpoints support filtering and searching:

**Search Example:**
```
GET /api/users/?search=john
```

**Filter Example:**
```
GET /api/moments/?user_id=1
GET /api/messages/?conversation=1
```

---

## Best Practices

1. **Always include Authorization header** for authenticated endpoints
2. **Handle token expiration** - use refresh token to get new access token
3. **Validate data** before sending requests
4. **Handle errors gracefully** - check response status codes
5. **Use pagination** for large datasets
6. **Cache responses** where appropriate
7. **Compress images** before uploading