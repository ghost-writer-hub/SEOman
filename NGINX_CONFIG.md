# Nginx Proxy Manager Configuration Examples

Add these proxy hosts in your Nginx Proxy Manager panel:

## 1. Frontend Proxy

**Proxy Hosts → Add Proxy Host**

- **Domain Names**: `seoman.yourdomain.com` (or your preferred domain)
- **Scheme**: `http`
- **Forward Hostname / IP**: `seoman-frontend` (container name)
- **Forward Port**: `3000`
- **Cache Assets**: Enable (optional)
- **Block Common Exploits**: Enable
- **Websockets Support**: Enable

**SSL Tab:**
- Enable SSL
- Request a Let's Encrypt certificate
- Force SSL: Enable

**Custom Locations** (optional):
```
Location: /_next/static
Scheme: http
Forward Hostname / IP: seoman-frontend
Forward Port: 3000
Advanced -> Custom Nginx Configuration:
expires 1y;
add_header Cache-Control "public, immutable";
```

## 2. Backend API Proxy

**Proxy Hosts → Add Proxy Host**

- **Domain Names**: `api.seoman.yourdomain.com`
- **Scheme**: `http`
- **Forward Hostname / IP**: `seoman-backend`
- **Forward Port**: `8000`
- **Block Common Exploits**: Enable

**SSL Tab:**
- Enable SSL
- Request a Let's Encrypt certificate
- Force SSL: Enable

**Custom Configuration** (under Advanced → Custom Nginx Configuration):
```nginx
# Add CORS headers if needed
add_header 'Access-Control-Allow-Origin' 'https://seoman.yourdomain.com' always;
add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
add_header 'Access-Control-Allow-Credentials' 'true' always;

# Handle preflight requests
if ($request_method = 'OPTIONS') {
    return 204;
}

# Increase timeout for long-running requests
proxy_read_timeout 300;
proxy_connect_timeout 300;
proxy_send_timeout 300;
```

## 3. Casdoor Web Proxy (Optional)

**Proxy Hosts → Add Proxy Host**

- **Domain Names**: `auth.seoman.yourdomain.com`
- **Scheme**: `http`
- **Forward Hostname / IP**: `seoman-casdoor-web`
- **Forward Port**: `8001`
- **Block Common Exploits**: Enable

**SSL Tab:**
- Enable SSL
- Request a Let's Encrypt certificate
- Force SSL: Enable

## 4. MinIO Console Proxy (Optional - Dev Only)

**Proxy Hosts → Add Proxy Host**

- **Domain Names**: `minio.seoman.yourdomain.com`
- **Scheme**: `http`
- **Forward Hostname / IP**: `seoman-minio`
- **Forward Port**: `9001`

**Custom Configuration** (under Advanced → Custom Nginx Configuration):
```nginx
# Websocket support needed for MinIO console
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

## Important Notes

1. **Update CORS_ORIGINS in .env**:
   After setting up your domains, update the `CORS_ORIGINS` variable in `.env`:
   ```
   CORS_ORIGINS=https://seoman.yourdomain.com,https://api.seoman.yourdomain.com
   ```

2. **Update frontend environment**:
   Update `NEXT_PUBLIC_API_URL` in `.env`:
   ```
   NEXT_PUBLIC_API_URL=https://api.seoman.yourdomain.com/api/v1
   NEXT_PUBLIC_CASDOOR_ENDPOINT=https://auth.seoman.yourdomain.com
   ```

3. **Restart containers** after changing environment variables:
   ```bash
   docker-compose restart frontend backend
   ```

4. **Security**:
   - Don't expose MinIO API (port 9000) publicly - use backend as proxy
   - Only expose Casdoor web if needed for management
   - Always use SSL for production

5. **Testing**:
   After configuration, test each endpoint:
   - `curl -I https://seoman.yourdomain.com`
   - `curl https://api.seoman.yourdomain.com/api/v1/health`
   - Access auth panel at `https://auth.seoman.yourdomain.com`
