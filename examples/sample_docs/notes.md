# Development Notes

## Auth Token Handling

The auth_token is validated on every request by the API gateway middleware.
Tokens expire after 24 hours and must be refreshed via the /auth/refresh endpoint.

## Database Migrations

All migrations run through Alembic. Never modify the database schema directly.
Run migrations with: `alembic upgrade head`
