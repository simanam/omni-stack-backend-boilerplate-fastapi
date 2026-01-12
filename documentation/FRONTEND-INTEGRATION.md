# Frontend Integration Guide

Everything frontend and mobile developers need to integrate with the OmniStack Backend API.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [TypeScript Types](#typescript-types)
4. [API Client Setup](#api-client-setup)
5. [Common Patterns](#common-patterns)
6. [Error Handling](#error-handling)
7. [Real-time & Streaming](#real-time--streaming)
8. [Next.js (App Router)](#nextjs-app-router)
9. [React Examples](#react-examples)
10. [Mobile (React Native)](#mobile-react-native)
11. [Native iOS (Swift)](#native-ios-swift)
12. [Native Android (Kotlin)](#native-android-kotlin)

---

## Quick Start

### Base URL

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
```

### Basic Request

```typescript
// Simple GET request
const response = await fetch(`${API_BASE_URL}/app/users/me`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
  },
});
const user = await response.json();
```

---

## Authentication

### With Supabase

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

// Get access token for API calls
async function getAccessToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

// Make authenticated request
async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = await getAccessToken();

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new APIError(error);
  }

  return response.json();
}
```

### With Clerk

```typescript
import { useAuth } from '@clerk/nextjs';

function MyComponent() {
  const { getToken } = useAuth();

  async function fetchData() {
    const token = await getToken();

    const response = await fetch(`${API_BASE_URL}/app/users/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    return response.json();
  }
}
```

### Token Refresh Pattern

```typescript
// The auth provider (Supabase/Clerk) handles token refresh automatically
// Just always call getSession()/getToken() before each request

async function makeRequest(endpoint: string) {
  // This always returns a fresh/valid token
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    // Redirect to login
    throw new Error('Not authenticated');
  }

  return fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Authorization': `Bearer ${session.access_token}`,
    },
  });
}
```

---

## TypeScript Types

### Core Types

```typescript
// ============================================
// Common Types
// ============================================

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

// Pagination helper
interface PaginationInfo {
  total: number;
  skip: number;
  limit: number;
  currentPage: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

function getPaginationInfo(response: PaginatedResponse<unknown>): PaginationInfo {
  const totalPages = Math.ceil(response.total / response.limit);
  const currentPage = Math.floor(response.skip / response.limit) + 1;

  return {
    total: response.total,
    skip: response.skip,
    limit: response.limit,
    currentPage,
    totalPages,
    hasNext: response.skip + response.items.length < response.total,
    hasPrev: response.skip > 0,
  };
}

// ============================================
// User Types
// ============================================

interface User {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: 'user' | 'admin' | 'superadmin';
  is_active: boolean;
  subscription_plan: 'free' | 'pro' | 'enterprise' | null;
  subscription_status: 'active' | 'canceled' | 'past_due' | 'trialing' | 'incomplete' | null;
  created_at: string; // ISO 8601
}

interface UserUpdate {
  full_name?: string;
  avatar_url?: string;
}

// ============================================
// Project Types
// ============================================

interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

interface ProjectCreate {
  name: string;
  description?: string;
}

interface ProjectUpdate {
  name?: string;
  description?: string;
}

type ProjectListResponse = PaginatedResponse<Project>;

// ============================================
// File Types
// ============================================

interface FileUploadRequest {
  filename: string;
  content_type: string;
  size: number;
}

interface PresignedUploadResponse {
  upload_url: string;
  file_id: string;
  key: string;
  expires_in: number;
}

interface FileRecord {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  status: 'pending' | 'uploaded' | 'failed';
  created_at: string;
}

interface DownloadUrlResponse {
  download_url: string;
  expires_in: number;
}

// ============================================
// AI Types
// ============================================

type MessageRole = 'system' | 'user' | 'assistant';

interface ChatMessage {
  role: MessageRole;
  content: string;
}

interface CompletionRequest {
  messages: ChatMessage[];
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

interface SimpleCompletionRequest {
  prompt: string;
  system?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

interface RoutedCompletionRequest {
  prompt: string;
  system?: string;
  complexity: 'simple' | 'moderate' | 'complex' | 'search';
  temperature?: number;
  max_tokens?: number;
}

interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

interface CompletionResponse {
  content: string;
  model: string;
  provider: string;
  usage: TokenUsage;
  finish_reason: string;
  latency_ms: number;
}

interface AIStatusResponse {
  available: boolean;
  providers: string[];
  default_provider: string;
  default_model: string;
}

// ============================================
// Billing Types
// ============================================

interface BillingStatus {
  plan: string;
  status: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  has_active_subscription: boolean;
}

interface CheckoutRequest {
  plan: 'monthly' | 'yearly';
  success_url: string;
  cancel_url: string;
}

interface CheckoutResponse {
  session_id: string;
  url: string;
}

interface PortalResponse {
  url: string;
}

interface Invoice {
  id: string;
  number: string | null;
  status: string;
  amount_due: number;
  amount_paid: number;
  currency: string;
  created: number;
  hosted_invoice_url: string | null;
  invoice_pdf: string | null;
}

// ============================================
// Usage Types
// ============================================

type UsageMetric =
  | 'api_requests'
  | 'ai_tokens'
  | 'ai_requests'
  | 'storage_bytes'
  | 'file_uploads'
  | 'file_downloads'
  | 'websocket_messages'
  | 'background_jobs'
  | 'email_sent';

interface UsageMetricInfo {
  current_period: number;
  previous_period: number;
  growth_rate: number;
  daily_average: number;
}

interface UsageSummaryResponse {
  metrics: Record<UsageMetric, UsageMetricInfo>;
  period: {
    start: string;
    end: string;
  };
}

interface UsageCurrentPeriodResponse {
  api_requests: number;
  ai_tokens: number;
  ai_requests: number;
  storage_bytes: number;
  file_uploads: number;
  file_downloads: number;
  websocket_messages: number;
  background_jobs: number;
  email_sent: number;
  period: {
    start: string;
    end: string;
  };
}

interface UsageTrendResponse {
  metric: UsageMetric;
  current_period: number;
  previous_period: number;
  growth_rate: number;
  daily_average: number;
  peak_day: string;
  peak_value: number;
  trend: 'increasing' | 'decreasing' | 'stable';
}

interface UsageDailyDataPoint {
  date: string;
  value: number;
}

interface UsageDailyResponse {
  metric: UsageMetric;
  data: UsageDailyDataPoint[];
  total: number;
  average: number;
}

interface UsageBreakdownResponse {
  metric: UsageMetric;
  breakdown: Record<string, number>;
  total: number;
}

interface UsageMetricDefinition {
  key: UsageMetric;
  name: string;
  description: string;
  unit: string;
}

interface UsageMetricsListResponse {
  metrics: UsageMetricDefinition[];
}

// ============================================
// Health Types
// ============================================

interface HealthResponse {
  status: string;
  timestamp: string;
}

interface HealthReadyResponse {
  status: string;
  timestamp: string;
  components: {
    database: { status: string };
    cache: { status: string };
  };
}
```

### Error Types

```typescript
// API Error codes
type ErrorCode =
  | 'BAD_REQUEST'
  | 'AUTHENTICATION_ERROR'
  | 'AUTHORIZATION_ERROR'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'VALIDATION_ERROR'
  | 'RATE_LIMIT_EXCEEDED'
  | 'EXTERNAL_SERVICE_ERROR'
  | 'SERVICE_UNAVAILABLE';

class APIError extends Error {
  code: ErrorCode;
  details: Record<string, unknown>;
  status: number;

  constructor(response: ErrorResponse, status: number = 400) {
    super(response.error.message);
    this.code = response.error.code as ErrorCode;
    this.details = response.error.details;
    this.status = status;
    this.name = 'APIError';
  }

  // Helper methods
  isNotFound(): boolean {
    return this.code === 'NOT_FOUND';
  }

  isAuthError(): boolean {
    return this.code === 'AUTHENTICATION_ERROR' || this.code === 'AUTHORIZATION_ERROR';
  }

  isRateLimited(): boolean {
    return this.code === 'RATE_LIMIT_EXCEEDED';
  }

  isValidationError(): boolean {
    return this.code === 'VALIDATION_ERROR';
  }
}
```

---

## API Client Setup

### Basic Fetch Wrapper

```typescript
// lib/api.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL!;

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number>;
}

async function getAuthToken(): Promise<string | null> {
  // Implement based on your auth provider
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

export async function api<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;

  // Build URL with query params
  let url = `${API_BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      searchParams.append(key, String(value));
    });
    url += `?${searchParams.toString()}`;
  }

  // Get auth token
  const token = await getAuthToken();

  // Make request
  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...fetchOptions.headers,
    },
  });

  // Handle errors
  if (!response.ok) {
    const errorData = await response.json();
    throw new APIError(errorData, response.status);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Convenience methods
export const apiClient = {
  get: <T>(endpoint: string, params?: Record<string, string | number>) =>
    api<T>(endpoint, { method: 'GET', params }),

  post: <T>(endpoint: string, data?: unknown) =>
    api<T>(endpoint, { method: 'POST', body: JSON.stringify(data) }),

  patch: <T>(endpoint: string, data?: unknown) =>
    api<T>(endpoint, { method: 'PATCH', body: JSON.stringify(data) }),

  delete: <T>(endpoint: string) =>
    api<T>(endpoint, { method: 'DELETE' }),
};
```

### Axios Client

```typescript
// lib/axios.ts

import axios, { AxiosError } from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
apiClient.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }

  return config;
});

// Response interceptor - handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    if (error.response) {
      throw new APIError(error.response.data, error.response.status);
    }
    throw error;
  }
);

export { apiClient };
```

### TanStack Query Setup

```typescript
// lib/query.ts

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error) => {
        // Don't retry on auth errors
        if (error instanceof APIError && error.isAuthError()) {
          return false;
        }
        return failureCount < 3;
      },
    },
  },
});

// Query keys factory
export const queryKeys = {
  user: {
    current: ['user', 'current'] as const,
  },
  projects: {
    all: ['projects'] as const,
    list: (params: { skip?: number; limit?: number; search?: string }) =>
      ['projects', 'list', params] as const,
    detail: (id: string) => ['projects', 'detail', id] as const,
  },
  billing: {
    status: ['billing', 'status'] as const,
    invoices: ['billing', 'invoices'] as const,
  },
  ai: {
    status: ['ai', 'status'] as const,
  },
  usage: {
    summary: ['usage', 'summary'] as const,
    currentPeriod: ['usage', 'current-period'] as const,
    trends: (metric: string) => ['usage', 'trends', metric] as const,
    daily: (metric: string, days: number) => ['usage', 'daily', metric, days] as const,
    breakdown: (metric: string) => ['usage', 'breakdown', metric] as const,
    metrics: ['usage', 'metrics'] as const,
  },
};
```

---

## Common Patterns

### Pagination

```typescript
// hooks/usePaginatedProjects.ts

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

interface UsePaginatedProjectsOptions {
  initialLimit?: number;
  search?: string;
}

export function usePaginatedProjects(options: UsePaginatedProjectsOptions = {}) {
  const { initialLimit = 20, search } = options;
  const [page, setPage] = useState(0);

  const query = useQuery({
    queryKey: queryKeys.projects.list({
      skip: page * initialLimit,
      limit: initialLimit,
      search,
    }),
    queryFn: () =>
      apiClient.get<ProjectListResponse>('/app/projects', {
        skip: page * initialLimit,
        limit: initialLimit,
        ...(search && { search }),
      }),
  });

  const pagination = query.data ? getPaginationInfo(query.data) : null;

  return {
    ...query,
    pagination,
    page,
    setPage,
    nextPage: () => setPage((p) => p + 1),
    prevPage: () => setPage((p) => Math.max(0, p - 1)),
  };
}
```

### Optimistic Updates

```typescript
// hooks/useUpdateProject.ts

import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectUpdate) =>
      apiClient.patch<Project>(`/app/projects/${projectId}`, data),

    // Optimistic update
    onMutate: async (newData) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: queryKeys.projects.detail(projectId),
      });

      // Snapshot previous value
      const previousProject = queryClient.getQueryData<Project>(
        queryKeys.projects.detail(projectId)
      );

      // Optimistically update
      if (previousProject) {
        queryClient.setQueryData(
          queryKeys.projects.detail(projectId),
          { ...previousProject, ...newData }
        );
      }

      return { previousProject };
    },

    // Rollback on error
    onError: (err, newData, context) => {
      if (context?.previousProject) {
        queryClient.setQueryData(
          queryKeys.projects.detail(projectId),
          context.previousProject
        );
      }
    },

    // Refetch after success or error
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.detail(projectId),
      });
    },
  });
}
```

### File Upload

```typescript
// hooks/useFileUpload.ts

interface UseFileUploadOptions {
  onProgress?: (progress: number) => void;
  onSuccess?: (file: FileRecord) => void;
  onError?: (error: Error) => void;
}

export function useFileUpload(options: UseFileUploadOptions = {}) {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const upload = async (file: File) => {
    setIsUploading(true);
    setProgress(0);

    try {
      // 1. Get presigned upload URL
      const presigned = await apiClient.post<PresignedUploadResponse>(
        '/app/files/upload-url',
        {
          filename: file.name,
          content_type: file.type,
          size: file.size,
        }
      );

      // 2. Upload to storage (with progress tracking)
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            setProgress(pct);
            options.onProgress?.(pct);
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            reject(new Error('Upload failed'));
          }
        });

        xhr.addEventListener('error', () => reject(new Error('Upload failed')));

        xhr.open('PUT', presigned.upload_url);
        xhr.setRequestHeader('Content-Type', file.type);
        xhr.send(file);
      });

      // 3. Confirm upload
      const fileRecord = await apiClient.post<FileRecord>(
        '/app/files/confirm',
        { file_id: presigned.file_id }
      );

      options.onSuccess?.(fileRecord);
      return fileRecord;

    } catch (error) {
      options.onError?.(error as Error);
      throw error;
    } finally {
      setIsUploading(false);
    }
  };

  return {
    upload,
    isUploading,
    progress,
  };
}
```

---

## Error Handling

### Global Error Handler

```typescript
// components/ErrorBoundary.tsx

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export function useAPIErrorHandler() {
  const router = useRouter();

  const handleError = (error: unknown) => {
    if (error instanceof APIError) {
      switch (error.code) {
        case 'AUTHENTICATION_ERROR':
          // Redirect to login
          router.push('/login');
          break;

        case 'AUTHORIZATION_ERROR':
          // Show forbidden page
          router.push('/403');
          break;

        case 'NOT_FOUND':
          // Show 404
          router.push('/404');
          break;

        case 'RATE_LIMIT_EXCEEDED':
          // Show rate limit message
          const retryAfter = error.details.retry_after as number;
          toast.error(`Too many requests. Try again in ${retryAfter} seconds.`);
          break;

        case 'VALIDATION_ERROR':
          // Show field-specific error
          const field = error.details.field as string;
          toast.error(`${field}: ${error.message}`);
          break;

        default:
          toast.error(error.message);
      }
    } else {
      toast.error('An unexpected error occurred');
      console.error(error);
    }
  };

  return handleError;
}
```

### Form Validation Errors

```typescript
// hooks/useFormWithAPI.ts

interface UseFormWithAPIOptions<T> {
  onSubmit: (data: T) => Promise<void>;
}

export function useFormWithAPI<T extends Record<string, unknown>>(
  options: UseFormWithAPIOptions<T>
) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (data: T) => {
    setErrors({});
    setIsSubmitting(true);

    try {
      await options.onSubmit(data);
    } catch (error) {
      if (error instanceof APIError && error.isValidationError()) {
        const field = error.details.field as string;
        if (field) {
          setErrors({ [field]: error.message });
        }
      } else {
        throw error;
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    errors,
    isSubmitting,
    handleSubmit,
    clearErrors: () => setErrors({}),
  };
}
```

---

## Real-time & Streaming

### AI Streaming with SSE

```typescript
// hooks/useStreamingCompletion.ts

interface UseStreamingCompletionOptions {
  onChunk?: (chunk: string) => void;
  onComplete?: (fullText: string) => void;
  onError?: (error: Error) => void;
}

export function useStreamingCompletion(options: UseStreamingCompletionOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [content, setContent] = useState('');

  const stream = async (request: SimpleCompletionRequest) => {
    setIsStreaming(true);
    setContent('');

    try {
      const token = await getAuthToken();

      const response = await fetch(`${API_BASE_URL}/app/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ ...request, stream: true }),
      });

      if (!response.ok) {
        throw new Error('Stream request failed');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      let fullContent = '';

      while (reader) {
        const { done, value } = await reader.read();

        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            if (data === '[DONE]') {
              break;
            }

            fullContent += data;
            setContent(fullContent);
            options.onChunk?.(data);
          }
        }
      }

      options.onComplete?.(fullContent);
      return fullContent;

    } catch (error) {
      options.onError?.(error as Error);
      throw error;
    } finally {
      setIsStreaming(false);
    }
  };

  return {
    stream,
    isStreaming,
    content,
    reset: () => setContent(''),
  };
}
```

### Usage in Component

```tsx
function ChatInterface() {
  const { stream, isStreaming, content, reset } = useStreamingCompletion();
  const [input, setInput] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    reset();

    await stream({
      prompt: input,
      system: 'You are a helpful assistant.',
    });

    setInput('');
  };

  return (
    <div>
      <div className="response">
        {content}
        {isStreaming && <span className="cursor">|</span>}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming}
        />
        <button type="submit" disabled={isStreaming}>
          Send
        </button>
      </form>
    </div>
  );
}
```

---

## Next.js (App Router)

### Project Setup

```bash
# Create Next.js app
npx create-next-app@latest my-app --typescript --tailwind --app

# Install dependencies
npm install @supabase/supabase-js @tanstack/react-query
```

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### Supabase Client (Client & Server)

```typescript
// lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

```typescript
// lib/supabase/server.ts
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Called from Server Component
          }
        },
      },
    }
  );
}
```

### API Client for Server Components

```typescript
// lib/api/server.ts
import { createClient } from '@/lib/supabase/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL!;

export async function serverApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(session?.access_token && {
        'Authorization': `Bearer ${session.access_token}`,
      }),
      ...options.headers,
    },
    // Important for Next.js caching
    cache: options.cache || 'no-store',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'API request failed');
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
```

### Server Component Example

```tsx
// app/dashboard/page.tsx
import { serverApi } from '@/lib/api/server';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

interface ProjectsResponse {
  items: Project[];
  total: number;
  skip: number;
  limit: number;
}

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    redirect('/login');
  }

  // Fetch data on the server
  const projects = await serverApi<ProjectsResponse>('/app/projects?limit=10');

  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome, {session.user.email}</p>

      <h2>Your Projects ({projects.total})</h2>
      <ul>
        {projects.items.map((project) => (
          <li key={project.id}>
            <h3>{project.name}</h3>
            <p>{project.description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Server Actions

```typescript
// app/actions/projects.ts
'use server';

import { revalidatePath } from 'next/cache';
import { serverApi } from '@/lib/api/server';

interface ProjectCreate {
  name: string;
  description?: string;
}

export async function createProject(data: ProjectCreate) {
  try {
    const project = await serverApi('/app/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    revalidatePath('/dashboard');
    return { success: true, project };
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }
}

export async function deleteProject(projectId: string) {
  try {
    await serverApi(`/app/projects/${projectId}`, {
      method: 'DELETE',
    });

    revalidatePath('/dashboard');
    return { success: true };
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }
}
```

### Client Component with Server Action

```tsx
// components/CreateProjectForm.tsx
'use client';

import { useFormStatus } from 'react-dom';
import { createProject } from '@/app/actions/projects';
import { useState } from 'react';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Creating...' : 'Create Project'}
    </button>
  );
}

export function CreateProjectForm() {
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(formData: FormData) {
    const result = await createProject({
      name: formData.get('name') as string,
      description: formData.get('description') as string || undefined,
    });

    if (!result.success) {
      setError(result.error || 'Failed to create project');
    }
  }

  return (
    <form action={handleSubmit}>
      {error && <p className="text-red-500">{error}</p>}

      <input
        name="name"
        placeholder="Project name"
        required
      />

      <textarea
        name="description"
        placeholder="Description (optional)"
      />

      <SubmitButton />
    </form>
  );
}
```

### Route Handler (API Route)

```typescript
// app/api/user/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL!;

export async function GET() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const response = await fetch(`${API_BASE_URL}/app/users/me`, {
    headers: {
      'Authorization': `Bearer ${session.access_token}`,
    },
  });

  const data = await response.json();
  return NextResponse.json(data);
}
```

### Middleware (Auth Protection)

```typescript
// middleware.ts
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          );
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { session } } = await supabase.auth.getSession();

  // Protect routes
  if (!session && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Redirect logged-in users away from auth pages
  if (session && request.nextUrl.pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return response;
}

export const config = {
  matcher: ['/dashboard/:path*', '/login', '/signup'],
};
```

### React Query Provider

```tsx
// app/providers.tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

```tsx
// app/layout.tsx
import { Providers } from './providers';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### Streaming AI Response in Next.js

```tsx
// app/api/ai/chat/route.ts
import { createClient } from '@/lib/supabase/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL!;

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    return new Response('Unauthorized', { status: 401 });
  }

  const body = await request.json();

  const response = await fetch(`${API_BASE_URL}/app/ai/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ ...body, stream: true }),
  });

  // Forward the stream
  return new Response(response.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

```tsx
// components/AIChat.tsx
'use client';

import { useState } from 'react';

export function AIChat() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsLoading(true);
    setResponse('');

    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: input }),
    });

    const reader = res.body?.getReader();
    const decoder = new TextDecoder();

    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          setResponse((prev) => prev + line.slice(6));
        }
      }
    }

    setIsLoading(false);
    setInput('');
  }

  return (
    <div>
      <div className="response">{response}</div>
      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
          placeholder="Ask something..."
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Thinking...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
```

---

## React Examples

### User Profile Component

```tsx
// components/UserProfile.tsx

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function UserProfile() {
  const queryClient = useQueryClient();

  const { data: user, isLoading } = useQuery({
    queryKey: queryKeys.user.current,
    queryFn: () => apiClient.get<User>('/app/users/me'),
  });

  const updateMutation = useMutation({
    mutationFn: (data: UserUpdate) =>
      apiClient.patch<User>('/app/users/me', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.user.current });
    },
  });

  if (isLoading) return <div>Loading...</div>;
  if (!user) return <div>Not found</div>;

  return (
    <div>
      <h1>{user.full_name || 'No name'}</h1>
      <p>{user.email}</p>
      <p>Plan: {user.subscription_plan || 'Free'}</p>

      <button
        onClick={() => updateMutation.mutate({ full_name: 'New Name' })}
        disabled={updateMutation.isPending}
      >
        Update Name
      </button>
    </div>
  );
}
```

### Projects List with Pagination

```tsx
// components/ProjectsList.tsx

export function ProjectsList() {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);

  const {
    data,
    isLoading,
    pagination,
    page,
    nextPage,
    prevPage,
  } = usePaginatedProjects({
    search: debouncedSearch,
  });

  return (
    <div>
      <input
        type="search"
        placeholder="Search projects..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <>
          <ul>
            {data?.items.map((project) => (
              <li key={project.id}>
                <h3>{project.name}</h3>
                <p>{project.description}</p>
              </li>
            ))}
          </ul>

          {pagination && (
            <div className="pagination">
              <button onClick={prevPage} disabled={!pagination.hasPrev}>
                Previous
              </button>
              <span>
                Page {pagination.currentPage} of {pagination.totalPages}
              </span>
              <button onClick={nextPage} disabled={!pagination.hasNext}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

### Billing Integration

```tsx
// components/BillingSection.tsx

export function BillingSection() {
  const { data: status, isLoading } = useQuery({
    queryKey: queryKeys.billing.status,
    queryFn: () => apiClient.get<BillingStatus>('/app/billing/status'),
  });

  const checkoutMutation = useMutation({
    mutationFn: (plan: 'monthly' | 'yearly') =>
      apiClient.post<CheckoutResponse>('/app/billing/checkout', {
        plan,
        success_url: `${window.location.origin}/billing/success`,
        cancel_url: `${window.location.origin}/billing/cancel`,
      }),
    onSuccess: (data) => {
      // Redirect to Stripe checkout
      window.location.href = data.url;
    },
  });

  const portalMutation = useMutation({
    mutationFn: () =>
      apiClient.get<PortalResponse>('/app/billing/portal', {
        return_url: window.location.href,
      }),
    onSuccess: (data) => {
      window.location.href = data.url;
    },
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <h2>Billing</h2>

      <p>Current Plan: {status?.plan}</p>
      <p>Status: {status?.status || 'No subscription'}</p>

      {status?.has_active_subscription ? (
        <button onClick={() => portalMutation.mutate()}>
          Manage Subscription
        </button>
      ) : (
        <div>
          <button
            onClick={() => checkoutMutation.mutate('monthly')}
            disabled={checkoutMutation.isPending}
          >
            Subscribe Monthly ($19/mo)
          </button>
          <button
            onClick={() => checkoutMutation.mutate('yearly')}
            disabled={checkoutMutation.isPending}
          >
            Subscribe Yearly ($190/yr)
          </button>
        </div>
      )}
    </div>
  );
}
```

### Usage Dashboard Component

```tsx
// components/UsageDashboard.tsx

import { useQuery } from '@tanstack/react-query';

export function UsageDashboard() {
  const { data: currentPeriod, isLoading: loadingCurrent } = useQuery({
    queryKey: queryKeys.usage.currentPeriod,
    queryFn: () => apiClient.get<UsageCurrentPeriodResponse>('/app/usage/current-period'),
  });

  const { data: aiTrends, isLoading: loadingTrends } = useQuery({
    queryKey: queryKeys.usage.trends('ai_tokens'),
    queryFn: () => apiClient.get<UsageTrendResponse>('/app/usage/trends', { metric: 'ai_tokens' }),
  });

  if (loadingCurrent || loadingTrends) return <div>Loading...</div>;

  return (
    <div className="usage-dashboard">
      <h2>Usage This Period</h2>

      <div className="metrics-grid">
        <MetricCard
          label="API Requests"
          value={currentPeriod?.api_requests ?? 0}
          unit="requests"
        />
        <MetricCard
          label="AI Tokens"
          value={currentPeriod?.ai_tokens ?? 0}
          unit="tokens"
          trend={aiTrends?.trend}
          growthRate={aiTrends?.growth_rate}
        />
        <MetricCard
          label="Storage"
          value={formatBytes(currentPeriod?.storage_bytes ?? 0)}
          unit=""
        />
        <MetricCard
          label="Files Uploaded"
          value={currentPeriod?.file_uploads ?? 0}
          unit="files"
        />
      </div>

      <div className="period-info">
        <small>
          Period: {new Date(currentPeriod?.period.start ?? '').toLocaleDateString()} -{' '}
          {new Date(currentPeriod?.period.end ?? '').toLocaleDateString()}
        </small>
      </div>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: number | string;
  unit: string;
  trend?: 'increasing' | 'decreasing' | 'stable';
  growthRate?: number;
}

function MetricCard({ label, value, unit, trend, growthRate }: MetricCardProps) {
  return (
    <div className="metric-card">
      <h3>{label}</h3>
      <p className="value">
        {typeof value === 'number' ? value.toLocaleString() : value} {unit}
      </p>
      {trend && growthRate !== undefined && (
        <p className={`trend ${trend}`}>
          {trend === 'increasing' ? '↑' : trend === 'decreasing' ? '↓' : '→'}
          {Math.abs(growthRate).toFixed(1)}% vs last period
        </p>
      )}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}
```

---

## Mobile (React Native)

### API Setup

```typescript
// lib/api.ts (React Native)

import * as SecureStore from 'expo-secure-store';

const API_BASE_URL = 'https://api.yourapp.com/api/v1';

async function getStoredToken(): Promise<string | null> {
  return SecureStore.getItemAsync('access_token');
}

export async function api<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getStoredToken();

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new APIError(error, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
```

### Auth Context

```tsx
// contexts/AuthContext.tsx (React Native)

import * as SecureStore from 'expo-secure-store';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: {
      async getItem(key) {
        return SecureStore.getItemAsync(key);
      },
      async setItem(key, value) {
        await SecureStore.setItemAsync(key, value);
      },
      async removeItem(key) {
        await SecureStore.deleteItemAsync(key);
      },
    },
  },
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        fetchUser();
      }
      setIsLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (session?.user) {
          await fetchUser();
        } else {
          setUser(null);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const fetchUser = async () => {
    try {
      const user = await api<User>('/app/users/me');
      setUser(user);
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  };

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
```

---

## Rate Limiting Handling

```typescript
// lib/rateLimiting.ts

interface RateLimitState {
  limit: number;
  remaining: number;
  reset: number;
}

let rateLimitState: RateLimitState | null = null;

// Update rate limit state from response headers
function updateRateLimitFromResponse(response: Response) {
  const limit = response.headers.get('X-RateLimit-Limit');
  const remaining = response.headers.get('X-RateLimit-Remaining');
  const reset = response.headers.get('X-RateLimit-Reset');

  if (limit && remaining && reset) {
    rateLimitState = {
      limit: parseInt(limit, 10),
      remaining: parseInt(remaining, 10),
      reset: parseInt(reset, 10),
    };
  }
}

// Check if we should wait before making a request
async function waitForRateLimit() {
  if (rateLimitState && rateLimitState.remaining === 0) {
    const now = Math.floor(Date.now() / 1000);
    const waitTime = rateLimitState.reset - now;

    if (waitTime > 0) {
      await new Promise((resolve) => setTimeout(resolve, waitTime * 1000));
    }
  }
}

// Enhanced fetch with rate limit handling
export async function rateLimitedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  await waitForRateLimit();

  const response = await fetch(url, options);
  updateRateLimitFromResponse(response);

  if (response.status === 429) {
    // Rate limited - wait and retry
    const retryAfter = parseInt(response.headers.get('Retry-After') || '60', 10);
    await new Promise((resolve) => setTimeout(resolve, retryAfter * 1000));
    return rateLimitedFetch(url, options);
  }

  return response;
}
```

---

## Native iOS (Swift)

### API Client

```swift
// APIClient.swift
import Foundation

enum APIError: Error {
    case invalidURL
    case noData
    case decodingError
    case serverError(code: String, message: String)
    case unauthorized
    case networkError(Error)
}

struct ErrorResponse: Codable {
    struct ErrorDetail: Codable {
        let code: String
        let message: String
        let details: [String: String]?
    }
    let error: ErrorDetail
}

class APIClient {
    static let shared = APIClient()

    private let baseURL = "https://api.yourapp.com/api/v1"
    private var accessToken: String?

    private init() {}

    func setAccessToken(_ token: String?) {
        self.accessToken = token
    }

    func request<T: Codable>(
        endpoint: String,
        method: String = "GET",
        body: Encodable? = nil
    ) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.networkError(NSError(domain: "Invalid response", code: 0))
        }

        // Handle 204 No Content
        if httpResponse.statusCode == 204 {
            // Return empty response for void types
            if let emptyResponse = EmptyResponse() as? T {
                return emptyResponse
            }
        }

        // Handle errors
        if httpResponse.statusCode >= 400 {
            if httpResponse.statusCode == 401 {
                throw APIError.unauthorized
            }

            if let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data) {
                throw APIError.serverError(
                    code: errorResponse.error.code,
                    message: errorResponse.error.message
                )
            }
            throw APIError.serverError(code: "UNKNOWN", message: "Request failed")
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw APIError.decodingError
        }
    }
}

struct EmptyResponse: Codable {}
```

### Models

```swift
// Models.swift
import Foundation

struct User: Codable {
    let id: String
    let email: String
    let fullName: String?
    let avatarUrl: String?
    let role: String
    let isActive: Bool
    let subscriptionPlan: String?
    let subscriptionStatus: String?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, email, role
        case fullName = "full_name"
        case avatarUrl = "avatar_url"
        case isActive = "is_active"
        case subscriptionPlan = "subscription_plan"
        case subscriptionStatus = "subscription_status"
        case createdAt = "created_at"
    }
}

struct Project: Codable {
    let id: String
    let name: String
    let description: String?
    let ownerId: String
    let createdAt: String
    let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, name, description
        case ownerId = "owner_id"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct ProjectCreate: Codable {
    let name: String
    let description: String?
}

struct ProjectUpdate: Codable {
    let name: String?
    let description: String?
}

struct PaginatedResponse<T: Codable>: Codable {
    let items: [T]
    let total: Int
    let skip: Int
    let limit: Int
}

struct BillingStatus: Codable {
    let plan: String
    let status: String?
    let currentPeriodEnd: String?
    let cancelAtPeriodEnd: Bool
    let hasActiveSubscription: Bool

    enum CodingKeys: String, CodingKey {
        case plan, status
        case currentPeriodEnd = "current_period_end"
        case cancelAtPeriodEnd = "cancel_at_period_end"
        case hasActiveSubscription = "has_active_subscription"
    }
}
```

### Auth Manager (with Supabase)

```swift
// AuthManager.swift
import Foundation
import Supabase

class AuthManager: ObservableObject {
    static let shared = AuthManager()

    private let supabase = SupabaseClient(
        supabaseURL: URL(string: "https://xxx.supabase.co")!,
        supabaseKey: "your-anon-key"
    )

    @Published var currentUser: User?
    @Published var isAuthenticated = false

    private init() {
        Task {
            await checkSession()
        }
    }

    func checkSession() async {
        do {
            let session = try await supabase.auth.session
            APIClient.shared.setAccessToken(session.accessToken)
            await fetchCurrentUser()
            await MainActor.run {
                self.isAuthenticated = true
            }
        } catch {
            await MainActor.run {
                self.isAuthenticated = false
            }
        }
    }

    func signIn(email: String, password: String) async throws {
        let session = try await supabase.auth.signIn(
            email: email,
            password: password
        )
        APIClient.shared.setAccessToken(session.accessToken)
        await fetchCurrentUser()
        await MainActor.run {
            self.isAuthenticated = true
        }
    }

    func signOut() async throws {
        try await supabase.auth.signOut()
        APIClient.shared.setAccessToken(nil)
        await MainActor.run {
            self.currentUser = nil
            self.isAuthenticated = false
        }
    }

    private func fetchCurrentUser() async {
        do {
            let user: User = try await APIClient.shared.request(endpoint: "/app/users/me")
            await MainActor.run {
                self.currentUser = user
            }
        } catch {
            print("Failed to fetch user: \(error)")
        }
    }
}
```

### SwiftUI Views

```swift
// ProjectsView.swift
import SwiftUI

struct ProjectsView: View {
    @State private var projects: [Project] = []
    @State private var isLoading = true
    @State private var error: String?

    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    ProgressView()
                } else if let error = error {
                    Text(error)
                        .foregroundColor(.red)
                } else {
                    List(projects, id: \.id) { project in
                        VStack(alignment: .leading) {
                            Text(project.name)
                                .font(.headline)
                            if let description = project.description {
                                Text(description)
                                    .font(.subheadline)
                                    .foregroundColor(.gray)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Projects")
            .task {
                await loadProjects()
            }
        }
    }

    private func loadProjects() async {
        do {
            let response: PaginatedResponse<Project> = try await APIClient.shared.request(
                endpoint: "/app/projects?limit=20"
            )
            await MainActor.run {
                self.projects = response.items
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.error = error.localizedDescription
                self.isLoading = false
            }
        }
    }
}
```

```swift
// CreateProjectView.swift
import SwiftUI

struct CreateProjectView: View {
    @Environment(\.dismiss) var dismiss
    @State private var name = ""
    @State private var description = ""
    @State private var isSubmitting = false
    @State private var error: String?

    var body: some View {
        NavigationView {
            Form {
                Section {
                    TextField("Project Name", text: $name)
                    TextField("Description (optional)", text: $description)
                }

                if let error = error {
                    Section {
                        Text(error)
                            .foregroundColor(.red)
                    }
                }
            }
            .navigationTitle("New Project")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        Task { await createProject() }
                    }
                    .disabled(name.isEmpty || isSubmitting)
                }
            }
        }
    }

    private func createProject() async {
        isSubmitting = true
        error = nil

        do {
            let _: Project = try await APIClient.shared.request(
                endpoint: "/app/projects",
                method: "POST",
                body: ProjectCreate(
                    name: name,
                    description: description.isEmpty ? nil : description
                )
            )
            await MainActor.run {
                dismiss()
            }
        } catch APIError.serverError(let code, let message) {
            await MainActor.run {
                self.error = message
                self.isSubmitting = false
            }
        } catch {
            await MainActor.run {
                self.error = error.localizedDescription
                self.isSubmitting = false
            }
        }
    }
}
```

---

## Native Android (Kotlin)

### Dependencies (build.gradle.kts)

```kotlin
// app/build.gradle.kts
dependencies {
    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    // ViewModel
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0")

    // Supabase
    implementation("io.github.jan-tennert.supabase:gotrue-kt:2.0.0")
    implementation("io.ktor:ktor-client-android:2.3.7")
}
```

### API Models

```kotlin
// models/ApiModels.kt
package com.yourapp.models

import com.google.gson.annotations.SerializedName

data class User(
    val id: String,
    val email: String,
    @SerializedName("full_name") val fullName: String?,
    @SerializedName("avatar_url") val avatarUrl: String?,
    val role: String,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("subscription_plan") val subscriptionPlan: String?,
    @SerializedName("subscription_status") val subscriptionStatus: String?,
    @SerializedName("created_at") val createdAt: String
)

data class Project(
    val id: String,
    val name: String,
    val description: String?,
    @SerializedName("owner_id") val ownerId: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String
)

data class ProjectCreate(
    val name: String,
    val description: String? = null
)

data class ProjectUpdate(
    val name: String? = null,
    val description: String? = null
)

data class PaginatedResponse<T>(
    val items: List<T>,
    val total: Int,
    val skip: Int,
    val limit: Int
)

data class ErrorResponse(
    val error: ErrorDetail
)

data class ErrorDetail(
    val code: String,
    val message: String,
    val details: Map<String, Any>?
)

data class BillingStatus(
    val plan: String,
    val status: String?,
    @SerializedName("current_period_end") val currentPeriodEnd: String?,
    @SerializedName("cancel_at_period_end") val cancelAtPeriodEnd: Boolean,
    @SerializedName("has_active_subscription") val hasActiveSubscription: Boolean
)
```

### API Service

```kotlin
// api/ApiService.kt
package com.yourapp.api

import com.yourapp.models.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    // Users
    @GET("app/users/me")
    suspend fun getCurrentUser(): User

    @PATCH("app/users/me")
    suspend fun updateCurrentUser(@Body update: Map<String, String?>): User

    // Projects
    @GET("app/projects")
    suspend fun getProjects(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20,
        @Query("search") search: String? = null
    ): PaginatedResponse<Project>

    @POST("app/projects")
    suspend fun createProject(@Body project: ProjectCreate): Project

    @GET("app/projects/{id}")
    suspend fun getProject(@Path("id") id: String): Project

    @PATCH("app/projects/{id}")
    suspend fun updateProject(
        @Path("id") id: String,
        @Body update: ProjectUpdate
    ): Project

    @DELETE("app/projects/{id}")
    suspend fun deleteProject(@Path("id") id: String): Response<Unit>

    // Billing
    @GET("app/billing/status")
    suspend fun getBillingStatus(): BillingStatus
}
```

### API Client

```kotlin
// api/ApiClient.kt
package com.yourapp.api

import com.google.gson.Gson
import com.yourapp.models.ErrorResponse
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private const val BASE_URL = "https://api.yourapp.com/api/v1/"

    private var accessToken: String? = null

    fun setAccessToken(token: String?) {
        accessToken = token
    }

    private val okHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor { chain ->
                val originalRequest = chain.request()
                val requestBuilder = originalRequest.newBuilder()
                    .header("Content-Type", "application/json")

                accessToken?.let {
                    requestBuilder.header("Authorization", "Bearer $it")
                }

                chain.proceed(requestBuilder.build())
            }
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            })
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseURL(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val apiService: ApiService by lazy {
        retrofit.create(ApiService::class.java)
    }
}

// Exception handling
class ApiException(
    val code: String,
    override val message: String,
    val details: Map<String, Any>? = null
) : Exception(message)

suspend fun <T> safeApiCall(apiCall: suspend () -> T): Result<T> {
    return try {
        Result.success(apiCall())
    } catch (e: retrofit2.HttpException) {
        val errorBody = e.response()?.errorBody()?.string()
        val errorResponse = try {
            Gson().fromJson(errorBody, ErrorResponse::class.java)
        } catch (ex: Exception) {
            null
        }

        Result.failure(
            ApiException(
                code = errorResponse?.error?.code ?: "UNKNOWN",
                message = errorResponse?.error?.message ?: "Request failed",
                details = errorResponse?.error?.details
            )
        )
    } catch (e: Exception) {
        Result.failure(e)
    }
}
```

### Auth Manager (with Supabase)

```kotlin
// auth/AuthManager.kt
package com.yourapp.auth

import com.yourapp.api.ApiClient
import com.yourapp.models.User
import io.github.jan.supabase.createSupabaseClient
import io.github.jan.supabase.gotrue.Auth
import io.github.jan.supabase.gotrue.auth
import io.github.jan.supabase.gotrue.providers.builtin.Email
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

object AuthManager {
    private val supabase = createSupabaseClient(
        supabaseUrl = "https://xxx.supabase.co",
        supabaseKey = "your-anon-key"
    ) {
        install(Auth)
    }

    private val _currentUser = MutableStateFlow<User?>(null)
    val currentUser: StateFlow<User?> = _currentUser

    private val _isAuthenticated = MutableStateFlow(false)
    val isAuthenticated: StateFlow<Boolean> = _isAuthenticated

    suspend fun checkSession() {
        try {
            val session = supabase.auth.currentSessionOrNull()
            if (session != null) {
                ApiClient.setAccessToken(session.accessToken)
                fetchCurrentUser()
                _isAuthenticated.value = true
            }
        } catch (e: Exception) {
            _isAuthenticated.value = false
        }
    }

    suspend fun signIn(email: String, password: String) {
        supabase.auth.signInWith(Email) {
            this.email = email
            this.password = password
        }

        val session = supabase.auth.currentSessionOrNull()
        ApiClient.setAccessToken(session?.accessToken)
        fetchCurrentUser()
        _isAuthenticated.value = true
    }

    suspend fun signOut() {
        supabase.auth.signOut()
        ApiClient.setAccessToken(null)
        _currentUser.value = null
        _isAuthenticated.value = false
    }

    private suspend fun fetchCurrentUser() {
        try {
            val user = ApiClient.apiService.getCurrentUser()
            _currentUser.value = user
        } catch (e: Exception) {
            // Handle error
        }
    }
}
```

### ViewModel

```kotlin
// viewmodels/ProjectsViewModel.kt
package com.yourapp.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourapp.api.ApiClient
import com.yourapp.api.safeApiCall
import com.yourapp.models.Project
import com.yourapp.models.ProjectCreate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class ProjectsViewModel : ViewModel() {

    private val _projects = MutableStateFlow<List<Project>>(emptyList())
    val projects: StateFlow<List<Project>> = _projects

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    private val _total = MutableStateFlow(0)
    val total: StateFlow<Int> = _total

    fun loadProjects(skip: Int = 0, limit: Int = 20) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            val result = safeApiCall {
                ApiClient.apiService.getProjects(skip = skip, limit = limit)
            }

            result.onSuccess { response ->
                _projects.value = response.items
                _total.value = response.total
            }.onFailure { e ->
                _error.value = e.message
            }

            _isLoading.value = false
        }
    }

    fun createProject(name: String, description: String?, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true

            val result = safeApiCall {
                ApiClient.apiService.createProject(
                    ProjectCreate(name = name, description = description)
                )
            }

            result.onSuccess {
                loadProjects() // Refresh list
                onSuccess()
            }.onFailure { e ->
                _error.value = e.message
            }

            _isLoading.value = false
        }
    }

    fun deleteProject(projectId: String) {
        viewModelScope.launch {
            val result = safeApiCall {
                ApiClient.apiService.deleteProject(projectId)
            }

            result.onSuccess {
                // Remove from local list
                _projects.value = _projects.value.filter { it.id != projectId }
            }.onFailure { e ->
                _error.value = e.message
            }
        }
    }
}
```

### Jetpack Compose UI

```kotlin
// ui/ProjectsScreen.kt
package com.yourapp.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.yourapp.viewmodels.ProjectsViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectsScreen(
    viewModel: ProjectsViewModel = viewModel()
) {
    val projects by viewModel.projects.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()

    var showCreateDialog by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        viewModel.loadProjects()
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Projects") })
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showCreateDialog = true }) {
                Text("+")
            }
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when {
                isLoading -> {
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                error != null -> {
                    Text(
                        text = error ?: "Error",
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                else -> {
                    LazyColumn {
                        items(projects) { project ->
                            ProjectItem(
                                project = project,
                                onDelete = { viewModel.deleteProject(project.id) }
                            )
                        }
                    }
                }
            }
        }
    }

    if (showCreateDialog) {
        CreateProjectDialog(
            onDismiss = { showCreateDialog = false },
            onCreate = { name, description ->
                viewModel.createProject(name, description) {
                    showCreateDialog = false
                }
            }
        )
    }
}

@Composable
fun ProjectItem(
    project: com.yourapp.models.Project,
    onDelete: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = project.name,
                style = MaterialTheme.typography.titleMedium
            )
            project.description?.let {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            TextButton(onClick = onDelete) {
                Text("Delete", color = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Composable
fun CreateProjectDialog(
    onDismiss: () -> Unit,
    onCreate: (name: String, description: String?) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("New Project") },
        text = {
            Column {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Name") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description (optional)") },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    onCreate(name, description.ifBlank { null })
                },
                enabled = name.isNotBlank()
            ) {
                Text("Create")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
```
