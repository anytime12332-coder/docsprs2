# DocuMind IDP API Reference

## Base URL

```
https://your-backend.railway.app/api
```

## Authentication

All endpoints (except `/auth/login`) require a Bearer token:

```
Authorization: Bearer <access_token>
```

### POST /auth/login

```json
{
  "email": "admin@documind.io",
  "password": "admin123456"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Documents

### POST /documents/upload

Multipart form upload:
- `file` (required): Document file
- `tags`: Comma-separated tags
- `notes`: Optional notes
- `auto_process`: Boolean, auto-process after upload
- `template_id`: UUID of template to use

### GET /documents

Query params: `page`, `per_page`, `status`, `document_type`, `search`, `is_archived`, `sort_by`, `sort_order`

### POST /documents/{id}/process

```json
{
  "extraction_method": "auto",
  "force_ocr": false,
  "language": "en"
}
```

### POST /documents/process/sync/{id}

Same as above but returns results synchronously.

## Extractions

### GET /extractions/document/{document_id}

Get all extraction results for a document.

### POST /extractions/correct

```json
{
  "corrections": [
    {"field_id": "uuid", "corrected_value": "new value"}
  ]
}
```

### POST /extractions/validate

```json
{
  "extraction_id": "uuid",
  "corrections": []
}
```

### GET /extractions/{id}/export?format=json

Export extraction results as JSON or CSV.

## Templates

### POST /templates

```json
{
  "name": "Invoice Template",
  "document_type": "invoice",
  "description": "Standard invoice extraction",
  "fields": [
    {
      "field_name": "invoice_number",
      "field_label": "Invoice Number",
      "field_type": "text",
      "is_required": true,
      "extraction_hint": "Invoice\\s*#?\\s*:?\\s*([A-Z0-9-]+)"
    }
  ]
}
```

## Webhooks

### POST /webhooks

```json
{
  "name": "My Webhook",
  "url": "https://example.com/webhook",
  "secret": "signing-secret",
  "events": ["document.processed", "extraction.completed"]
}
```

## Admin

### GET /admin/stats

System-wide statistics.

### GET /admin/audit-logs

Query params: `page`, `per_page`, `action`, `resource_type`, `user_id`

### GET /admin/config

Current system configuration (non-sensitive).
