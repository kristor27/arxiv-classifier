<script lang="ts">
	import { ORDER, VERDICTS } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import type { Verdict } from '$lib/types';

	// Edits per minute over the last 30 minutes, stacked by verdict: Wikipedia's heartbeat.
	const W = 320, H = 110, PAD_B = 18, MINUTES = 30;
	let hover = $state<number | null>(null);

	const buckets = $derived.by(() => {
		const end = Math.floor(live.now / 60000) * 60;
		const rows = Array.from({ length: MINUTES }, (_, i) => ({
			t: end - (MINUTES - 1 - i) * 60,
			n: { disruptive: 0, good_faith_error: 0, improvement: 0 } as Record<Verdict, number>
		}));
		for (const p of live.stats?.pulse ?? []) {
			const row = rows.find((r) => r.t === p.t);
			if (row) row.n[p.verdict] = p.n;
		}
		return rows;
	});
	const max = $derived(Math.max(10, ...buckets.map((b) => ORDER.reduce((s, v) => s + b.n[v], 0))));
	const bw = W / MINUTES;
	const y = (n: number) => (n / max) * (H - PAD_B);
</script>

<section class="card p-5">
	<div class="flex items-baseline justify-between">
		<h2 class="text-sm font-semibold">Pulse</h2>
		<span class="text-xs text-muted">edits per minute · last 30 min</span>
	</div>
	<ul class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-text-2">
		{#each ORDER as v (v)}
			<li class="flex items-center gap-1.5"><span class="size-2 rounded-sm" style="background: {VERDICTS[v].color}"></span>{VERDICTS[v].label}</li>
		{/each}
	</ul>
	<div class="relative mt-2">
		<svg viewBox="0 0 {W} {H}" class="w-full" role="img" aria-label="Edits per minute by verdict, last 30 minutes">
			{#each [0.5, 1] as f (f)}
				<line x1="0" x2={W} y1={H - PAD_B - (H - PAD_B) * f} y2={H - PAD_B - (H - PAD_B) * f} stroke="var(--border)" stroke-dasharray="2 3" />
			{/each}
			<text x="0" y="8" class="fill-muted text-[8px]">{max}/min</text>
			{#each buckets as b, i (b.t)}
				{@const total = ORDER.reduce((s, v) => s + b.n[v], 0)}
				<g opacity={hover === null || hover === i ? 1 : 0.45}>
					{#each ORDER.toReversed() as v, k (v)}
						{@const below = ORDER.toReversed().slice(0, k).reduce((s, u) => s + b.n[u], 0)}
						{#if b.n[v]}
							<rect x={i * bw + 1} width={bw - 2} y={H - PAD_B - y(below + b.n[v]) + (below ? 1 : 0)}
								height={Math.max(1, y(b.n[v]) - (below ? 1 : 0))} rx="1.5" fill={VERDICTS[v].color} />
						{/if}
					{/each}
				</g>
				<rect x={i * bw} width={bw} y="0" height={H} fill="transparent" role="presentation"
					onmouseenter={() => (hover = i)} onmouseleave={() => (hover = null)} />
				{#if total === 0}<rect x={i * bw + 1} width={bw - 2} y={H - PAD_B - 1} height="1" fill="var(--border)" />{/if}
			{/each}
			<text x="0" y={H - 4} class="fill-muted text-[8px]">−30 min</text>
			<text x={W} y={H - 4} text-anchor="end" class="fill-muted text-[8px]">now</text>
		</svg>
		{#if hover !== null}
			{@const b = buckets[hover]}
			<div class="pointer-events-none absolute top-0 z-10 rounded-lg bg-surface px-2.5 py-1.5 text-[11px] shadow-[var(--glow)]"
				style="left: clamp(0px, {(hover / MINUTES) * 100}% - 60px, calc(100% - 130px))">
				<p class="font-medium">{new Date(b.t * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
				{#each ORDER as v (v)}<p class="num text-text-2">{VERDICTS[v].label}: {b.n[v]}</p>{/each}
			</div>
		{/if}
	</div>
</section>
