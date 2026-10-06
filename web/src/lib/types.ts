export interface Judgement {
	engine: 'jev' | 'llm';
	model: string;
	label: string;
	category: string;
	confidence: number; // Jev: calibrated probability; LLM: self-reported, 0–1
	probabilities: Record<string, number> | null; // Jev only
	paper_type: string;
	ms: number;
	tokens_in: number;
	tokens_out: number;
	cost: number;
}

export interface Paper {
	id: string;
	url: string;
	title: string;
	abstract: string;
	authors: string;
	primary_category: string; // ground truth
	categories: string[];
	published: string;
	created_at: string;
	jev: Judgement;
	llm: Judgement | null;
}

export type Curve = { threshold: number; coverage: number; accuracy: number | null }[];
export type Calibration = { confidence: number; accuracy: number; n: number }[];

export interface Stats {
	n: number; // papers both judges answered
	total: number;
	with_llm: number;
	jev_accuracy: number | null;
	llm_accuracy: number | null;
	jev_lenient: number | null;
	llm_lenient: number | null;
	agreement: number | null;
	jev_p50_ms: number | null;
	jev_p95_ms: number | null;
	llm_p50_ms: number | null;
	llm_p95_ms: number | null;
	jev_cost_per_paper: number | null;
	llm_cost_per_paper: number | null;
	jev_tokens_in: number | null;
	llm_tokens_in: number | null;
	llm_tokens_out: number | null;
	jev_spent: number;
	llm_spent: number;
	per_category: { category: string; n: number; jev: number; llm: number }[];
	confusions: Record<'jev' | 'llm', { truth: string; predicted: string; n: number }[]>;
	jev_coverage: Curve;
	llm_coverage: Curve;
	jev_calibration: Calibration;
	llm_calibration: Calibration;
	latency: { jev: number[]; llm: number[] };
	paused: boolean;
	categories: Record<string, string>;
	engines: { jev: string; llm: string | null };
}

export type Only = 'jev_wrong' | 'llm_wrong' | 'disagree';
