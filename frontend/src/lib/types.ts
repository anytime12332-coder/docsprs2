// Auth
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  avatar_url?: string;
  last_login?: string;
  created_at: string;
  updated_at: string;
}

// Documents
export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  document_type?: string;
  classification_confidence?: number;
  language?: string;
  status: string;
  error_message?: string;
  page_count?: number;
  metadata_json?: Record<string, any>;
  tags?: string[];
  notes?: string;
  is_duplicate: boolean;
  requires_review: boolean;
  is_archived: boolean;
  uploaded_by: string;
  template_id?: string;
  processing_started_at?: string;
  processing_completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  per_page: number;
}

// Extractions
export interface ExtractionField {
  id: string;
  field_name: string;
  field_value?: string;
  field_type: string;
  confidence?: number;
  page_number?: number;
  bounding_box?: Record<string, number>;
  is_corrected: boolean;
  original_value?: string;
  created_at: string;
}

export interface ExtractionTable {
  id: string;
  table_name?: string;
  headers?: string[];
  rows?: any[][];
  page_number?: number;
  confidence?: number;
  created_at: string;
}

export interface ExtractionResult {
  id: string;
  document_id: string;
  extraction_method: string;
  overall_confidence?: number;
  validated: boolean;
  validated_by?: string;
  validated_at?: string;
  version: number;
  fields: ExtractionField[];
  tables: ExtractionTable[];
  created_at: string;
}

// Templates
export interface TemplateField {
  id: string;
  field_name: string;
  field_label: string;
  field_type: string;
  is_required: boolean;
  default_value?: string;
  validation_regex?: string;
  extraction_hint?: string;
  order: number;
  anchor_text?: string;
  relative_position?: Record<string, any>;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  description?: string;
  document_type: string;
  is_active: boolean;
  version: number;
  preprocessing_config?: Record<string, any>;
  classification_keywords?: string[];
  validation_rules?: Record<string, any>;
  post_processing_config?: Record<string, any>;
  fields: TemplateField[];
  created_at: string;
  updated_at: string;
}

// Webhooks
export interface Webhook {
  id: string;
  name: string;
  url: string;
  is_active: boolean;
  events: string[];
  headers?: Record<string, string>;
  retry_count: number;
  timeout_seconds: number;
  created_at: string;
  updated_at: string;
}

// Stats
export interface SystemStats {
  total_documents: number;
  total_pages_processed: number;
  total_extractions: number;
  documents_today: number;
  processing_queue_size: number;
  storage_used_mb: number;
  avg_processing_time_seconds: number;
  success_rate: number;
  active_users: number;
  active_templates: number;
  active_webhooks: number;
}

// Audit
export interface AuditLog {
  id: string;
  user_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}
