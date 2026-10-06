import type { Verdict } from './types';

export const VERDICTS: Record<Verdict, { label: string; color: string; icon: string }> = {
	disruptive: { label: 'Disruptive', color: 'var(--crit)', icon: '✕' },
	good_faith_error: { label: 'Good-faith error', color: 'var(--warn)', icon: '!' },
	improvement: { label: 'Improvement', color: 'var(--good)', icon: '✓' }
};
export const TOPICS: Record<string, string> = {
	people: 'People',
	sports: 'Sports',
	entertainment: 'Entertainment',
	politics: 'Politics',
	history: 'History',
	geography: 'Places',
	science: 'Science & tech',
	business: 'Business',
	culture: 'Culture'
};
export const ORDER: Verdict[] = ['disruptive', 'good_faith_error', 'improvement'];

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

export const int = (v: number) => Intl.NumberFormat('en').format(Math.round(v));

export function ago(iso: string, now: number): string {
	const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
	if (s < 60) return `${s}s ago`;
	if (s < 3600) return `${Math.floor(s / 60)}m ago`;
	return `${Math.floor(s / 3600)}h ago`;
}

export const ratio = (a: number | null | undefined, b: number | null | undefined) =>
	a && b ? Math.round(b / a) : null;
