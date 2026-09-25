# Automatic IND JWT Token Refresh

This project refreshes all tokens from `Uid_ind.json` automatically every 8 hours using:

`https://ff-ob54-jwt-api.vercel.app/guest_to_jwt?uid={uid}&password={password}`

The response field used is `jwt_token`. The generated tokens are saved to `token_ind.json`. GitHub Actions commits the refreshed file automatically.

Keep the repository private because `Uid_ind.json` contains credentials.
