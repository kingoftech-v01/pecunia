# Accounts App

User authentication, registration, and profile management.

## Overview

The accounts app handles all user-related functionality:

- User registration and login (JWT)
- Profile management
- Password reset
- Token refresh and logout

## Models

### User

Custom user model with email-based authentication.

```python
class User(AbstractBaseUser, PermissionsMixin):
    id = UUIDField(primary_key=True)
    email = EmailField(unique=True)
    password = CharField()  # Argon2 hashed
    is_active = BooleanField(default=True)
    subscription_tier = CharField()  # free, premium, pro
    preferred_currency = CharField(default='EUR')
    created_at = DateTimeField(auto_now_add=True)
```

### UserProfile

Extended user information.

```python
class UserProfile(Model):
    user = OneToOneField(User)
    full_name = CharField()
    phone = CharField(blank=True)
    preferences = JSONField(default=dict)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/accounts/register/` | POST | User registration |
| `/api/v1/accounts/login/` | POST | User login (returns JWT) |
| `/api/v1/accounts/logout/` | POST | Logout (blacklist token) |
| `/api/v1/accounts/token/refresh/` | POST | Refresh access token |
| `/api/v1/accounts/users/me/` | GET/PATCH | Current user details |
| `/api/v1/accounts/users/me/change-password/` | POST | Change password |
| `/api/v1/accounts/profile/` | GET/PATCH | User profile |

## Authentication Flow

```
1. POST /register/ → Create user → Return tokens
2. POST /login/    → Validate credentials → Return tokens
3. Use access_token in Authorization header
4. When expired, POST /token/refresh/ with refresh_token
5. POST /logout/ → Blacklist refresh token
```

## Serializers

- `UserSerializer` - Full user details
- `UserCreateSerializer` - Registration with validation
- `LoginSerializer` - Email/password validation
- `PasswordChangeSerializer` - Password change validation

## Security

- Passwords hashed with Argon2
- JWT tokens with 60-minute access, 7-day refresh
- Token rotation and blacklisting enabled
- Account lockout after 5 failed attempts

## Testing

```bash
pytest apps/accounts/tests/ -v
```

## Related

- [SECURITY_GUIDELINES.md](../../../SECURITY_GUIDELINES.md) - Auth requirements
- [WEB_CONVENTIONS.md](../../WEB_CONVENTIONS.md) - Django patterns
