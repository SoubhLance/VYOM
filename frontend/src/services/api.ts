export interface AskRequestPayload {
  query: string;
  top_k?: number;
  multi?: boolean;
}

export interface Clip {
  clip_id: string;
  audio_url: string;
  partial: boolean;
  spoken_lines: string[];
}

export interface Source {
  verse_id: string;
  sanskrit?: string;
  transliteration?: string;
  is_neighbor?: boolean;
  neighbor_of?: string | null;
  for_question?: number[];
  clips?: Clip[];
}

export interface AskResponseData {
  query: string;
  routed: boolean | string;
  cited_verses: string[];
  answer: string;
  sub_questions?: string[];
  warnings?: string[];
  sources?: Source[];
}

/** Debug details from the response headers (X-VYOM-Cache, X-LLM-Provider, X-LLM-Model, X-LLM-Fallback) */
export interface AskMeta {
  cache?: string;
  provider?: string;
  model?: string;
  fallback?: boolean;
}

export interface HealthResponseData {
  status: string;
  searcher_ready?: boolean;
  valid_ids_count?: number;
}

/**
 * Why a question failed. "aborted" = the user pressed Stop.
 * busy: 429 / 503 (rate limit, every provider cooling down) · server: other 5xx or an unreadable body ·
 * bad_request: other 4xx · timeout: no answer within ASK_TIMEOUT_MS ·
 * network: the server could not be reached (fetch failed, or a proxy answered 502 / 504).
 */
export type AskErrorKind = 'aborted' | 'busy' | 'server' | 'bad_request' | 'timeout' | 'network';

export class AskError extends Error {
  readonly kind: AskErrorKind;
  readonly status?: number;
  constructor(kind: AskErrorKind, status?: number) {
    super(status ? `${kind} (HTTP ${status})` : kind);
    this.name = 'AskError';
    this.kind = kind;
    this.status = status;
  }
}

/** Multi-question answers can take a while (several retrievals, one LLM call, quote verification) */
const ASK_TIMEOUT_MS = 90000;

/**
 * Check backend health status
 */
export async function checkBackendHealth(): Promise<{ online: boolean; details?: HealthResponseData }> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);
    const res = await fetch('/api/health', {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data: HealthResponseData = await res.json();
      return { online: true, details: data };
    }
    return { online: false };
  } catch {
    return { online: false };
  }
}

/**
 * Ask VYOM. Resolves with the answer and its debug headers; every failure rejects with an AskError.
 * Never invents an answer: if the backend can't answer, the caller shows an error.
 */
export async function askGitaQuestion(
  payload: AskRequestPayload,
  options: { signal?: AbortSignal } = {},
): Promise<{ data: AskResponseData; meta: AskMeta }> {
  const { signal } = options;
  if (signal?.aborted) throw new AskError('aborted');

  // One controller for both the caller's Stop and our timeout, so we can tell which one fired
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, ASK_TIMEOUT_MS);
  const onCallerAbort = () => controller.abort();
  signal?.addEventListener('abort', onCallerAbort, { once: true });

  try {
    let res: Response;
    try {
      res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: payload.query, top_k: payload.top_k ?? 5, multi: payload.multi ?? true }),
        signal: controller.signal,
      });
    } catch {
      if (signal?.aborted) throw new AskError('aborted');
      if (timedOut) throw new AskError('timeout');
      throw new AskError('network');
    }

    if (res.status === 429 || res.status === 503) throw new AskError('busy', res.status);
    // 502 / 504 come from a proxy (Vite in dev) when the backend is down or unreachable
    if (res.status === 502 || res.status === 504) throw new AskError('network', res.status);
    if (res.status >= 500) throw new AskError('server', res.status);
    if (!res.ok) throw new AskError('bad_request', res.status);

    let data: AskResponseData;
    try {
      data = (await res.json()) as AskResponseData;
    } catch {
      if (signal?.aborted) throw new AskError('aborted');
      if (timedOut) throw new AskError('timeout');
      throw new AskError('server', res.status);
    }
    if (typeof data?.answer !== 'string') throw new AskError('server', res.status);

    const meta: AskMeta = {
      cache: res.headers.get('X-VYOM-Cache') ?? undefined,
      provider: res.headers.get('X-LLM-Provider') ?? undefined,
      model: res.headers.get('X-LLM-Model') ?? undefined,
      fallback: res.headers.get('X-LLM-Fallback') === 'true' || undefined,
    };
    return {
      data: {
        ...data,
        cited_verses: data.cited_verses ?? [],
        sub_questions: data.sub_questions ?? [],
        warnings: data.warnings ?? [],
        sources: data.sources ?? [],
      },
      meta,
    };
  } finally {
    clearTimeout(timeoutId);
    signal?.removeEventListener('abort', onCallerAbort);
  }
}

/** What the conversation shows for each failure. Plain words, no answer-shaped content. */
export function askErrorText(kind: AskErrorKind, status?: number): string {
  switch (kind) {
    case 'aborted':
      return 'Stopped. Nothing was answered.';
    case 'busy':
      return 'VYOM is catching its breath — try again in a few seconds.';
    case 'timeout':
      return 'VYOM took too long to answer. Please try again.';
    case 'network':
      return 'VYOM’s server can’t be reached right now. Please try again in a moment.';
    case 'bad_request':
      return `VYOM couldn’t read that question${status ? ` (error ${status})` : ''}. Try rephrasing it.`;
    case 'server':
    default:
      return `Something went wrong on VYOM’s side${status ? ` (error ${status})` : ''}. Please try again.`;
  }
}
