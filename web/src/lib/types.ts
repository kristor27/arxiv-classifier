export type Verdict = 'disruptive' | 'good_faith_error' | 'improvement';

export interface Judgement {
	engine: 'jev' | 'llm';
	model: string;
	label?: string; // display name of the comparison LLM, e.g. "Claude Sonnet 5.5"
	verdict: Verdict;
	confidence: number | null;
	probabilities: Record<Verdict, number> | null;
	kind: string;
	topic?: string; // missing on edits judged before topics were added
	severity: number;
	ms: number;
	tokens_in: number;
	tokens_out: number;
	cost: number;
}

export interface Edit {
	rev: number;
	wiki: string;
	title: string;
	url: string;
	editor: string;
	anonymous: boolean;
	comment: string;
	byte_delta: number;
	removed: string;
	added: string;
	context: string;
	created_at: string;
	jev: Judgement;
	llm: Judgement | null;
	reverted: boolean | null;
	checked_at: string | null;
}

export interface Stats {
	total: number;
	disruptive: number;
	good_faith_error: number;
	improvement: number;
	jev_cost: number;
	jev_cost_per_edit: number;
	jev_p50_ms: number | null;
	llm_n: number;
	llm_cost: number;
	llm_cost_per_edit: number | null;
	llm_p50_ms: number | null;
	agreement: number | null;
	checked: number;
	reverted: number;
	caught: number;
	flagged_checked: number;
	flagged_reverted: number;
	all_wikimedia_edits_per_s: number;
	llm_cost_if_all: number | null;
	jev_cost_per_year_all_wikimedia: number;
	llm_cost_per_year_all_wikimedia: number | null;
	pulse: { t: number; verdict: Verdict; n: number }[];
	latency: { jev: number[]; llm: number[] };
	engines: { jev: string; llm: string | null };
	paused: boolean;
	topics: { topic: string; n: number; disruptive: number }[];
	topic_names: string[];
}
