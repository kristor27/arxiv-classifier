/** Short names for the 12 arXiv categories in the label set. */
export const CATEGORY_NAMES: Record<string, string> = {
	'cs.AI': 'Artificial intelligence',
	'cs.CL': 'Language',
	'cs.CV': 'Vision',
	'cs.LG': 'Machine learning',
	'cs.RO': 'Robotics',
	'cs.CR': 'Security',
	'cs.SE': 'Software eng.',
	'cs.IR': 'Retrieval',
	'cs.HC': 'Human-computer',
	'cs.DC': 'Distributed',
	'cs.NI': 'Networking',
	'cs.DB': 'Databases'
};

export function usd(v: number | null | undefined): string {
	if (v == null) return '—';
	if (v >= 1000) return '$' + Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(v);
	if (v >= 1) return '$' + v.toFixed(2);
	if (v === 0) return '$0';
	return '$' + v.toPrecision(2);
}

export function ms(v: number | null | undefined): string {
	if (v == null) return '—';
	return v >= 1000 ? (v / 1000).toFixed(1) + ' s' : Math.round(v) + ' ms';
}

export const pct = (v: number | null | undefined, digits = 0) => (v == null ? '—' : (v * 100).toFixed(digits) + '%');
export const int = (v: number) => Intl.NumberFormat('en').format(Math.round(v));

export function ago(iso: string, now: number): string {
	const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
	if (s < 60) return `${s}s ago`;
	if (s < 3600) return `${Math.floor(s / 60)}m ago`;
	if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
	return `${Math.floor(s / 86400)}d ago`;
}

/** How many times bigger b is than a, for "6× faster" style labels. */
export const times = (a: number | null | undefined, b: number | null | undefined) => (a && b ? b / a : null);
export const fmtTimes = (x: number | null) => (x == null ? '—' : x >= 10 ? `${Math.round(x)}×` : `${x.toFixed(1)}×`);
