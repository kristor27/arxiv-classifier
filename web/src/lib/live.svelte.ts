import type { Edit, Stats, Verdict } from './types';

const MAX_FEED = 60;

/** The live state of the dashboard: a WebSocket for new verdicts, and stats polled every few seconds. */
class Live {
	edits = $state<Edit[]>([]);
	queued = $state<Edit[]>([]);
	stats = $state<Stats | null>(null);
	connected = $state(false);
	frozen = $state(false);
	filter = $state<{ verdict: Verdict | null; topic: string | null }>({ verdict: null, topic: null });
	arrivals = $state<{ id: number; verdict: string }[]>([]);
	now = $state(Date.now());

	start() {
		this.load();
		this.connect();
		this.poll();
		const timers = [setInterval(() => this.poll(), 3000), setInterval(() => (this.now = Date.now()), 1000)];
		return () => timers.forEach(clearInterval);
	}

	/** Filters run on the server, so a rare topic still fills the feed with its history. */
	setFilter(f: Partial<typeof this.filter>) {
		this.filter = { ...this.filter, ...f };
		this.queued = [];
		this.load();
	}

	private async load() {
		const q = new URLSearchParams({ limit: '40' });
		if (this.filter.verdict) q.set('verdict', this.filter.verdict);
		if (this.filter.topic) q.set('topic', this.filter.topic);
		try {
			this.edits = await (await fetch(`/api/edits?${q}`)).json();
		} catch {
			/* API restarting */
		}
	}

	private matches(e: Edit) {
		const { verdict, topic } = this.filter;
		return (!verdict || e.jev.verdict === verdict) && (!topic || e.jev.topic === topic);
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

	private receive(edit: Edit) {
		// One travelling dot per edit in the pipeline diagram, filtered or not.
		this.arrivals = [...this.arrivals.slice(-12), { id: edit.rev, verdict: edit.jev.verdict }];
		if (!this.matches(edit)) return;
		if (this.frozen) this.queued = [edit, ...this.queued].slice(0, MAX_FEED);
		else this.edits = [edit, ...this.edits].slice(0, MAX_FEED);
	}

	toggleFreeze() {
		this.frozen = !this.frozen;
		if (!this.frozen) {
			this.edits = [...this.queued, ...this.edits].slice(0, MAX_FEED);
			this.queued = [];
		}
	}

	/** Stop or resume sending edits to the judges — this is what stops the API bill. */
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
