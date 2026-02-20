/**
 * CORTEX SDK — Thin TypeScript client for the CORTEX Memory API.
 *
 * Zero dependencies. Uses native fetch().
 *
 * @example
 * ```ts
 * import { Cortex } from '@cortex-memory/sdk'
 *
 * const ctx = new Cortex({ url: 'http://localhost:8000', apiKey: 'sk-xxx' })
 * await ctx.store('user prefers dark mode', { project: 'myapp' })
 * const results = await ctx.search('preferences')
 * const ok = await ctx.verify()
 * ```
 */

// ── Types ─────────────────────────────────────────────────────

export interface CortexOptions {
  /** CORTEX API server URL (e.g. "http://localhost:8000") */
  url: string;
  /** API key for authentication (Authorization: Bearer <key>) */
  apiKey?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
}

export interface Fact {
  id: number;
  project: string;
  content: string;
  factType: string;
  tags: string[];
  confidence: string;
  score?: number;
  createdAt?: string;
  txId?: number;
  hash?: string;
  context?: Record<string, unknown>;
}

export interface StoreOptions {
  project?: string;
  factType?: string;
  tags?: string[];
  source?: string;
  meta?: Record<string, unknown>;
}

export interface SearchOptions {
  topK?: number;
  project?: string;
  asOf?: string;
  graphDepth?: number;
  includeGraph?: boolean;
}

export interface LedgerReport {
  valid: boolean;
  violations: string[];
  txChecked: number;
  rootsChecked: number;
  votesChecked: number;
}

export interface GraphData {
  nodes: Array<{ id: string; label: string; type: string }>;
  edges: Array<{ source: string; target: string; relation: string }>;
}

// ── Error ─────────────────────────────────────────────────────

export class CortexError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`[${status}] ${detail}`);
    this.name = "CortexError";
  }
}

// ── Client ────────────────────────────────────────────────────

export class Cortex {
  private baseUrl: string;
  private apiKey: string;
  private timeout: number;

  constructor(options: CortexOptions) {
    this.baseUrl = options.url.replace(/\/+$/, "");
    this.apiKey = options.apiKey ?? "";
    this.timeout = options.timeout ?? 30_000;
  }

  // ── Core Operations ───────────────────────────────────────

  /** Store a fact in CORTEX. Returns the fact ID. */
  async store(content: string, options: StoreOptions = {}): Promise<number> {
    const body: Record<string, unknown> = {
      project: options.project ?? "default",
      content,
      fact_type: options.factType ?? "general",
    };
    if (options.tags) body.tags = options.tags;
    if (options.source) body.source = options.source;
    if (options.meta) body.meta = options.meta;

    const resp = await this.post<{ fact_id: number }>("/v1/facts", body);
    return resp.fact_id;
  }

  /** Semantic search across stored facts. */
  async search(query: string, options: SearchOptions = {}): Promise<Fact[]> {
    const body: Record<string, unknown> = {
      query,
      k: options.topK ?? 5,
    };
    if (options.project) body.project = options.project;
    if (options.asOf) body.as_of = options.asOf;
    if (options.graphDepth) body.graph_depth = options.graphDepth;
    if (options.includeGraph) body.include_graph = options.includeGraph;

    const results = await this.post<Array<Record<string, unknown>>>(
      "/v1/search",
      body,
    );
    return results.map(toFact);
  }

  /** Recall all facts for a project. */
  async recall(project: string, limit?: number): Promise<Fact[]> {
    const params = limit ? `?limit=${limit}` : "";
    const results = await this.get<Array<Record<string, unknown>>>(
      `/v1/projects/${encodeURIComponent(project)}/facts${params}`,
    );
    return results.map(toFact);
  }

  /** Soft-deprecate a fact. */
  async deprecate(factId: number): Promise<boolean> {
    const resp = await this.del<{ success: boolean }>(`/v1/facts/${factId}`);
    return resp.success;
  }

  // ── Ledger Operations ─────────────────────────────────────

  /** Verify cryptographic integrity of the entire ledger. */
  async verify(): Promise<LedgerReport> {
    const r = await this.get<Record<string, unknown>>("/v1/ledger/verify");
    return {
      valid: r.valid as boolean,
      violations: (r.violations as string[]) ?? [],
      txChecked: (r.tx_checked as number) ?? 0,
      rootsChecked: (r.roots_checked as number) ?? 0,
      votesChecked: (r.votes_checked as number) ?? 0,
    };
  }

  /** Create a Merkle root checkpoint. */
  async checkpoint(): Promise<{
    checkpointId: number | null;
    message: string;
  }> {
    const r = await this.post<Record<string, unknown>>(
      "/v1/ledger/checkpoint",
      {},
    );
    return {
      checkpointId: (r.checkpoint_id as number | null) ?? null,
      message: (r.message as string) ?? "",
    };
  }

  // ── Graph Operations ──────────────────────────────────────

  /** Get the entity knowledge graph. */
  async graph(project?: string, limit = 50): Promise<GraphData> {
    const path = project
      ? `/v1/graph/${encodeURIComponent(project)}?limit=${limit}`
      : `/v1/graph?limit=${limit}`;
    return this.get<GraphData>(path);
  }

  // ── Voting ────────────────────────────────────────────────

  /** Cast a consensus vote on a fact. */
  async vote(
    factId: number,
    value: "verify" | "dispute" = "verify",
  ): Promise<Record<string, unknown>> {
    return this.post(`/v1/facts/${factId}/vote`, { value });
  }

  // ── HTTP Primitives (native fetch, zero deps) ─────────────

  private headers(): Record<string, string> {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (this.apiKey) h["Authorization"] = `Bearer ${this.apiKey}`;
    return h;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(url, {
        method,
        headers: this.headers(),
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!resp.ok) {
        const text = await resp.text();
        let detail: string;
        try {
          detail = JSON.parse(text).detail ?? text;
        } catch {
          detail = text;
        }
        throw new CortexError(resp.status, detail);
      }

      return (await resp.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }

  private get<T>(path: string): Promise<T> {
    return this.request<T>("GET", path);
  }

  private post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>("POST", path, body);
  }

  private del<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }
}

// ── Helpers ───────────────────────────────────────────────────

function toFact(data: Record<string, unknown>): Fact {
  return {
    id: (data.fact_id ?? data.id ?? 0) as number,
    project: (data.project ?? "") as string,
    content: (data.content ?? "") as string,
    factType: (data.fact_type ?? "general") as string,
    tags: (data.tags ?? []) as string[],
    confidence: (data.confidence ?? "medium") as string,
    score: data.score as number | undefined,
    createdAt: data.created_at as string | undefined,
    txId: data.tx_id as number | undefined,
    hash: data.hash as string | undefined,
    context: data.context as Record<string, unknown> | undefined,
  };
}

export default Cortex;
