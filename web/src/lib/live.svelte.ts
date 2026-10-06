import type { Only, Paper, Stats } from './types';

const MAX_FEED = 60;

/** The live state of the dashboard: a WebSocket for new verdicts, and stats polled every few seconds. */
class Live {
	papers = $state<Paper[]>([]);
	queued = $state<Paper[]>([]);
	stats = $state<Stats | null>(null);
	connected = $state(false);
	frozen = $state(false);
	filter = $state<{ category: string | null; only: Only | null }>({ category: null, only: null });
	arrivals = $state<{ id: string; ok: boolean }[]>([]);
	now = $state(Date.now());

	start() {
		this.load();
		this.connect();
		this.poll();
		const timers = [setInterval(() => this.poll(), 3000), setInterval(() => (this.now = Date.now()), 1000)];
		return () => timers.forEach(clearInterval);
	}

	/** Filters run on the server, so the feed fills with history that matches, not just new arrivals. */
	setFilter(f: Partial<typeof this.filter>) {
		this.filter = { ...this.filter, ...f };
		this.queued = [];
		this.load();
	}

	private async load() {
		const q = new URLSearchParams({ limit: '40' });
		if (this.filter.category) q.set('category', this.filter.category);
		if (this.filter.only) q.set('only', this.filter.only);
		try {
			this.papers = await (await fetch(`/api/papers?${q}`)).json();
		} catch {
			/* API restarting */
		}
	}

	private matches(p: Paper) {
		const { category, only } = this.filter;
		if (category && p.primary_category !== category) return false;
		if (only === 'jev_wrong') return p.jev.category !== p.primary_category;
		if (only === 'llm_wrong') return !!p.llm && p.llm.category !== p.primary_category;
		if (only === 'disagree') return !!p.llm && p.llm.category !== p.jev.category;
		return true;
	}

	private connect() {
		const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/live`);
		ws.onopen = () => (this.connected = true);
		ws.onclose = () => {
			this.connected = false;
			setTimeout(() => this.connect(), 2000);
		};
		ws.onmessage = (m) => this.receive(JSON.parse(m.data));
	}

	private receive(p: Paper) {
		// One travelling dot per paper in the pipeline diagram, green if Jev got it right.
		this.arrivals = [...this.arrivals.slice(-12), { id: p.id, ok: p.jev.category === p.primary_category }];
		if (!this.matches(p)) return;
		if (this.frozen) this.queued = [p, ...this.queued].slice(0, MAX_FEED);
		else this.papers = [p, ...this.papers].slice(0, MAX_FEED);
	}

	toggleFreeze() {
		this.frozen = !this.frozen;
		if (!this.frozen) {
			this.papers = [...this.queued, ...this.papers].slice(0, MAX_FEED);
			this.queued = [];
		}
	}

	/** Stop or resume judging new papers — this is what stops the API bill. */
	async setPaused(paused: boolean) {
		await fetch('/api/pipeline', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ paused }) });
		if (this.stats) this.stats.paused = paused;
	}

	private async poll() {
		try {
			this.stats = await (await fetch('/api/stats')).json();
		} catch {
			/* API restarting: keep the last stats */
		}
	}
}

export const live = new Live();
