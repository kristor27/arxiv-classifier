<script lang="ts">
	import { pct } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import type { Calibration, Curve } from '$lib/types';

	const W = 320, H = 170, L = 34, B = 24, T = 8, R = 10;
	const s = $derived(live.stats);
	const llm = $derived(s?.engines.llm ?? 'LLM');

	// Chart 1: keep only answers at or above a confidence threshold. x = share of papers kept, y = accuracy on them.
	const curves = $derived(
		(['jev', 'llm'] as const).map((e) => ({
			e,
			pts: ((s?.[`${e}_coverage`] ?? []) as Curve).filter((p) => p.accuracy != null && p.coverage > 0)
		}))
	);
	const yMin = $derived(Math.max(0, Math.floor(Math.min(1, ...curves.flatMap((c) => c.pts.map((p) => p.accuracy!))) * 10) / 10 - 0.1));
	const x = (v: number) => L + v * (W - L - R);
	const y = (v: number, lo: number) => T + (1 - (v - lo) / (1 - lo)) * (H - T - B);
	const path = (pts: { x: number; y: number }[]) => pts.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
	let hoverT = $state<number | null>(null);
	const at = (e: 'jev' | 'llm', t: number) => (s?.[`${e}_coverage`] as Curve | undefined)?.find((p) => p.threshold === t);

	// Chart 2: reliability diagram. On the diagonal, "80% sure" means right 80% of the time.
	const cal = $derived((['jev', 'llm'] as const).map((e) => ({ e, pts: (s?.[`${e}_calibration`] ?? []) as Calibration })));
	const maxN = $derived(Math.max(1, ...cal.flatMap((c) => c.pts.map((p) => p.n))));
</script>

<figure class="card p-5">
	<figcaption class="caption"><b>Figure 3.</b>Act only when sure. Each point keeps only the answers at or above a confidence threshold: further left means fewer papers sorted automatically, at higher accuracy.</figcaption>
	<ul class="mt-2 flex gap-3 text-[11px] text-text-2">
		<li class="flex items-center gap-1.5"><span class="h-0.5 w-3 rounded bg-jev"></span>Jev (probability)</li>
		<li class="flex items-center gap-1.5"><span class="h-0.5 w-3 rounded bg-llm"></span>{llm} (self-reported)</li>
	</ul>
	<svg viewBox="0 0 {W} {H}" class="mt-2 w-full overflow-visible" role="img" aria-label="Accuracy against the share of papers kept, for both models">
		{#each [yMin, (yMin + 1) / 2, 1] as v (v)}
			<line x1={L} x2={W - R} y1={y(v, yMin)} y2={y(v, yMin)} stroke="var(--border)" stroke-dasharray="2 3" />
			<text x={L - 4} y={y(v, yMin) + 3} text-anchor="end" class="fill-muted text-[8px]">{pct(v)}</text>
		{/each}
		{#each [0, 0.5, 1] as v (v)}
			<text x={x(v)} y={H - 8} text-anchor="middle" class="fill-muted text-[8px]">{pct(v)} kept</text>
		{/each}
		{#each curves as c (c.e)}
			<path d={path(c.pts.map((p) => ({ x: x(p.coverage), y: y(p.accuracy!, yMin) })))} fill="none" stroke="var(--{c.e})" stroke-width="2" stroke-linejoin="round" />
			{#each c.pts as p (p.threshold)}
				<circle cx={x(p.coverage)} cy={y(p.accuracy!, yMin)} r={hoverT === p.threshold ? 4.5 : 2.5} fill="var(--{c.e})" stroke="var(--surface)" stroke-width="1.5"
					role="presentation" onmouseenter={() => (hoverT = p.threshold)} onmouseleave={() => (hoverT = null)} />
			{/each}
		{/each}
	</svg>
	<p class="num mt-1 min-h-8 text-[11px] text-text-2">
		{#if hoverT != null}
			{@const j = at('jev', hoverT)}{@const g = at('llm', hoverT)}
			Confidence ≥ {pct(hoverT)}: Jev keeps {pct(j?.coverage)} at {pct(j?.accuracy, 1)} · {llm} keeps {pct(g?.coverage)} at {pct(g?.accuracy, 1)}
		{:else if at('jev', 0.9)?.accuracy != null}
			{@const j = at('jev', 0.9)!}{@const g = at('llm', 0.9)}
			At confidence ≥ 90%, Jev auto-sorts {pct(j.coverage)} of papers at {pct(j.accuracy, 1)} accuracy{#if g?.accuracy != null}; {llm} {pct(g.coverage)} at {pct(g.accuracy, 1)}{/if}. Hover a point for other thresholds.
		{/if}
	</p>

</figure>

<figure class="card p-5">
	<figcaption class="caption"><b>Figure 4.</b>Does the confidence mean anything? On the dashed line, "80% sure" is right 80% of the time. Jev's confidence is a probability; the LLM's is the number it wrote. Dot size is the number of papers.</figcaption>
	<ul class="mt-3 flex gap-3 text-[11px] text-text-2">
		<li class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-jev"></span>Jev</li>
		<li class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-llm"></span>{llm}</li>
	</ul>
	<svg viewBox="0 0 {W} {H}" class="mt-2 w-full overflow-visible" role="img" aria-label="Calibration of both models: stated confidence against observed accuracy">
		<line x1={x(0)} y1={y(0, 0)} x2={x(1)} y2={y(1, 0)} stroke="var(--muted)" stroke-dasharray="3 3" />
		{#each [0, 0.5, 1] as v (v)}
			<text x={L - 4} y={y(v, 0) + 3} text-anchor="end" class="fill-muted text-[8px]">{pct(v)}</text>
			<text x={x(v)} y={H - 8} text-anchor="middle" class="fill-muted text-[8px]">{pct(v)} sure</text>
		{/each}
		{#each cal as c (c.e)}
			<path d={path(c.pts.map((p) => ({ x: x(p.confidence), y: y(p.accuracy, 0) })))} fill="none" stroke="var(--{c.e})" stroke-width="2" stroke-opacity="0.6" />
			{#each c.pts as p, i (i)}
				<circle cx={x(p.confidence)} cy={y(p.accuracy, 0)} r={2.5 + 4 * Math.sqrt(p.n / maxN)} fill="var(--{c.e})" fill-opacity="0.85" stroke="var(--surface)" stroke-width="1.5">
					<title>{c.e === 'jev' ? 'Jev' : llm}: {p.n} papers at ~{pct(p.confidence)} confidence, {pct(p.accuracy)} right</title>
				</circle>
			{/each}
		{/each}
	</svg>
</figure>
