<script lang="ts">
	import { ms } from '$lib/format';
	import { live } from '$lib/live.svelte';

	// Every measured response time, one dot each, on a log scale: the gap is the story.
	const W = 320, ROW = 34, LEFT = 0, TICKS = [100, 300, 1000, 3000, 10000];
	const lo = Math.log10(80), hi = Math.log10(15000);
	const x = (v: number) => LEFT + ((Math.log10(Math.min(Math.max(v, 80), 15000)) - lo) / (hi - lo)) * (W - LEFT);
	const median = (a: number[]) => (a.length ? [...a].sort((p, q) => p - q)[Math.floor(a.length / 2)] : null);
	// Deterministic jitter so dots don't jump on every refresh.
	const jitter = (i: number) => ((i * 7919) % 17) / 17 - 0.5;

	const rows = $derived([
		{ key: 'jev', label: 'Jev', data: live.stats?.latency.jev ?? [] },
		{ key: 'llm', label: live.stats?.engines.llm ?? 'LLM', data: live.stats?.latency.llm ?? [] }
	]);
	let hover = $state<string | null>(null);
</script>

<section class="card p-5">
	<div class="flex items-baseline justify-between">
		<h2 class="text-sm font-semibold">Response time</h2>
		<span class="text-xs text-muted">every call · log scale</span>
	</div>
	<svg viewBox="0 0 {W} {ROW * 2 + 18}" class="mt-3 w-full overflow-visible" role="img"
		aria-label="Response times: Jev median {ms(median(rows[0].data))}, {rows[1].label} median {ms(median(rows[1].data))}">
		{#each TICKS as t (t)}
			<line x1={x(t)} x2={x(t)} y1="0" y2={ROW * 2} stroke="var(--border)" stroke-dasharray="2 3" />
			<text x={x(t)} y={ROW * 2 + 12} text-anchor="middle" class="fill-muted text-[8px]">{ms(t)}</text>
		{/each}
		{#each rows as r, ri (r.key)}
			{@const m = median(r.data)}
			<g role="presentation" onmouseenter={() => (hover = r.key)} onmouseleave={() => (hover = null)}>
				<rect x="0" y={ri * ROW} width={W} height={ROW} fill="transparent" />
				{#each r.data as v, i (i)}
					<circle cx={x(v)} cy={ri * ROW + ROW / 2 + jitter(i) * (ROW - 14)} r="2.2" fill="var(--{r.key})" opacity="0.55" />
				{/each}
				{#if m}
					<line x1={x(m)} x2={x(m)} y1={ri * ROW + 4} y2={ri * ROW + ROW - 4} stroke="var(--text)" stroke-width="2" stroke-linecap="round" />
					<text x={x(m) + 5} y={ri * ROW + 11} class="fill-text text-[9px] font-semibold">{r.label} {ms(m)}</text>
				{:else}
					<text x="4" y={ri * ROW + ROW / 2 + 3} class="fill-muted text-[9px]">{r.label}: no samples yet</text>
				{/if}
			</g>
		{/each}
	</svg>
	<p class="num mt-1 h-4 text-[11px] text-muted">
		{#if hover}
			{@const r = rows.find((q) => q.key === hover)!}
			{r.label}: {r.data.length} calls · median {ms(median(r.data))} · slowest {ms(Math.max(0, ...r.data) || null)}
		{/if}
	</p>
</section>
