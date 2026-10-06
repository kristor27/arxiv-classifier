<script lang="ts">
	import { ms, usd, VERDICTS } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import type { Judgement } from '$lib/types';
	import ProbBar from './ProbBar.svelte';
	import VerdictBadge from './VerdictBadge.svelte';

	const PRESETS = [
		{ name: 'Sneaky fake fact', title: 'Marie Curie', anonymous: true,
			removed: 'She was the first woman to win a Nobel Prize.',
			added: 'She was the first woman to win a Nobel Prize, and in 1902 she also invented the microwave oven.' },
		{ name: 'Honest mistake', title: 'Mount Everest', anonymous: false,
			removed: "Its elevation of 8,849 m was most recently established in 2020 by Chinese and Nepali authorities.",
			added: "Its elevation of 8,849 m (I think it's actually about 9,000 m now because of the snow) was most recently established in 2020." },
		{ name: 'Real improvement', title: 'Photosynthesis', anonymous: false, removed: '',
			added: 'In plants, photosynthesis mainly takes place in the chloroplasts of leaf mesophyll cells.<ref>{{cite book |title=Biology 2e |publisher=OpenStax |year=2018}}</ref>' },
		{ name: 'Blatant', title: 'Paris', anonymous: true,
			removed: 'Paris is the capital and largest city of France.', added: 'lol paris sucks' }
	];

	type Lane = { engine: 'jev' | 'llm'; label: string; elapsed: number; result: Judgement | null; error: string | null };
	let form = $state({ ...PRESETS[0] });
	let lanes = $state<Lane[]>([]);
	let running = $state(false);

	// Both requests leave at the same instant. The bars grow in real time, on the same scale.
	async function race() {
		running = true;
		lanes = [
			{ engine: 'jev', label: 'Jev', elapsed: 0, result: null, error: null },
			{ engine: 'llm', label: live.stats?.engines.llm ?? 'LLM', elapsed: 0, result: null, error: null }
		];
		const t0 = performance.now();
		let frame = requestAnimationFrame(function tick() {
			for (const l of lanes) if (!l.result && !l.error) l.elapsed = performance.now() - t0;
			frame = requestAnimationFrame(tick);
		});
		const body = JSON.stringify({ title: form.title, removed: form.removed, added: form.added, anonymous: form.anonymous });
		await Promise.all(
			lanes.map(async (lane) => {
				try {
					const r = await fetch(`/api/judge/${lane.engine}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body });
					const data = await r.json();
					lane.elapsed = performance.now() - t0;
					if (r.ok) lane.result = data;
					else lane.error = data.detail?.includes('402') || data.detail?.includes('credit') ? 'Out of API credits' : String(data.detail ?? r.status).slice(0, 80);
				} catch {
					lane.error = 'Network error';
				}
			})
		);
		cancelAnimationFrame(frame);
		running = false;
	}

	const scale = $derived(Math.max(2000, ...lanes.map((l) => l.elapsed)));
	const [jev, gem] = $derived([lanes[0]?.result, lanes[1]?.result]);
</script>

<section class="card p-5">
	<div class="flex items-baseline justify-between gap-2">
		<h2 class="text-sm font-semibold whitespace-nowrap">The race</h2>
		<p class="text-right text-xs text-muted">Same edit, same questions, same instant</p>
	</div>

	<div class="mt-3 flex flex-wrap gap-1.5">
		{#each PRESETS as p (p.name)}
			<button onclick={() => (form = { ...p })}
				class="rounded-full border px-2.5 py-1 text-xs transition {form.title === p.title ? 'border-jev bg-jev/10 text-jev' : 'border-border text-text-2 hover:border-muted'}">
				{p.name}
			</button>
		{/each}
	</div>

	<div class="mt-3 grid gap-2 text-sm">
		<label class="grid gap-1"><span class="text-xs text-muted">Article</span>
			<input bind:value={form.title} maxlength="300" class="rounded-lg border border-border bg-surface-2 px-3 py-1.5 outline-jev" /></label>
		<label class="grid gap-1"><span class="text-xs text-muted">Removed text</span>
			<textarea bind:value={form.removed} maxlength="1500" rows="2" class="resize-none rounded-lg border border-border bg-surface-2 px-3 py-1.5 font-mono text-xs outline-jev"></textarea></label>
		<label class="grid gap-1"><span class="text-xs text-muted">Added text</span>
			<textarea bind:value={form.added} maxlength="1500" rows="3" class="resize-none rounded-lg border border-border bg-surface-2 px-3 py-1.5 font-mono text-xs outline-jev"></textarea></label>
		<label class="flex items-center gap-2 text-xs text-text-2"><input type="checkbox" bind:checked={form.anonymous} class="accent-jev" /> Anonymous editor</label>
	</div>

	<button onclick={race} disabled={running}
		class="mt-3 w-full rounded-lg bg-jev py-2 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-60">
		{running ? 'Racing…' : 'Race ⚡'}
	</button>

	{#if lanes.length}
		<div class="mt-4 grid gap-3">
			{#each lanes as lane (lane.engine)}
				<div>
					<div class="mb-1 flex items-center justify-between text-xs">
						<span class="inline-flex items-center gap-1.5 font-medium"><span class="size-2 rounded-full" style="background: var(--{lane.engine})"></span>{lane.label}</span>
						<span class="num font-mono {lane.result ? 'text-text' : 'text-muted'}">{ms(lane.elapsed)}</span>
					</div>
					<div class="h-2 overflow-hidden rounded-full bg-surface-2">
						<div class="h-full rounded-full {lane.error ? 'opacity-30' : ''}" style="width: {(lane.elapsed / scale) * 100}%; background: var(--{lane.engine})"></div>
					</div>
					<div class="mt-2 min-h-6">
						{#if lane.result}
							<div class="flex flex-wrap items-center gap-2 text-xs text-muted">
								<VerdictBadge verdict={lane.result.verdict} size="sm" />
								<span>severity <span class="num">{lane.result.severity.toFixed(1)}</span>/3</span>
								<span class="num">{usd(lane.result.cost)}</span>
								<span class="num">{lane.result.tokens_in} in · {lane.result.tokens_out} out</span>
							</div>
							{#if lane.result.probabilities}
								<div class="mt-2"><ProbBar probs={lane.result.probabilities} /></div>
							{:else}
								<p class="mt-1 text-[11px] text-muted">One generated answer, no probabilities.</p>
							{/if}
						{:else if lane.error}
							<p class="text-xs text-warn">⚠ {lane.error}</p>
						{/if}
					</div>
				</div>
			{/each}
		</div>
		{#if jev && gem}
			<p class="mt-2 rounded-lg bg-jev/10 px-3 py-2 text-center text-sm text-text">
				Jev answered <b class="num">{Math.max(1, Math.round(gem.ms / jev.ms))}×</b> faster for
				<b class="num">{Math.max(1, Math.round(gem.cost / jev.cost))}×</b> less money{gem.verdict === jev.verdict ? ' — same verdict.' : ` — they disagree (${VERDICTS[gem.verdict].label.toLowerCase()}).`}
			</p>
		{/if}
	{/if}
</section>
