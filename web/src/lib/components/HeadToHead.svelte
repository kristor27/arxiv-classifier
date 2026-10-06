<script lang="ts">
	import { fmtTimes, int, ms, pct, times, usd } from '$lib/format';
	import { live } from '$lib/live.svelte';

	// Every row is measured on the same papers: the ones both models answered.
	const s = $derived(live.stats);
	const llm = $derived(s?.engines.llm ?? 'LLM');
	type Row = { label: string; hint: string; jev: string; llm: string; better: 'jev' | 'llm' | null; note: string };
	const rows = $derived.by<Row[]>(() => {
		if (!s || !s.n) return [];
		const acc = (a: number | null, b: number | null) => (a == null || b == null || a === b ? null : a > b ? 'jev' : 'llm');
		const pts = (a: number | null, b: number | null) => (a == null || b == null ? '' : `${Math.abs((a - b) * 100).toFixed(1)} pts`);
		const fast = (a: number | null, b: number | null) => (a == null || b == null ? null : a < b ? 'jev' : 'llm');
		return [
			{ label: 'Accuracy', hint: 'picks the exact primary category the authors chose',
				jev: pct(s.jev_accuracy, 1), llm: pct(s.llm_accuracy, 1), better: acc(s.jev_accuracy, s.llm_accuracy), note: pts(s.jev_accuracy, s.llm_accuracy) },
			{ label: 'Lenient accuracy', hint: 'picks any category the authors listed (primary or cross-list)',
				jev: pct(s.jev_lenient, 1), llm: pct(s.llm_lenient, 1), better: acc(s.jev_lenient, s.llm_lenient), note: pts(s.jev_lenient, s.llm_lenient) },
			{ label: 'Median response', hint: 'half of the answers came back faster than this',
				jev: ms(s.jev_p50_ms), llm: ms(s.llm_p50_ms), better: fast(s.jev_p50_ms, s.llm_p50_ms), note: `${fmtTimes(times(s.jev_p50_ms, s.llm_p50_ms))} faster` },
			{ label: 'Slow answers (p95)', hint: '95% of the answers came back faster than this',
				jev: ms(s.jev_p95_ms), llm: ms(s.llm_p95_ms), better: fast(s.jev_p95_ms, s.llm_p95_ms), note: `${fmtTimes(times(s.jev_p95_ms, s.llm_p95_ms))} faster` },
			{ label: 'Cost per 1,000 papers', hint: 'from each response’s real token counts and list prices',
				jev: usd((s.jev_cost_per_paper ?? 0) * 1000), llm: usd((s.llm_cost_per_paper ?? 0) * 1000),
				better: fast(s.jev_cost_per_paper, s.llm_cost_per_paper), note: `${fmtTimes(times(s.jev_cost_per_paper, s.llm_cost_per_paper))} cheaper` },
			{ label: 'Cost per million papers', hint: 'the same, at production volume',
				jev: usd((s.jev_cost_per_paper ?? 0) * 1e6), llm: usd((s.llm_cost_per_paper ?? 0) * 1e6),
				better: fast(s.jev_cost_per_paper, s.llm_cost_per_paper), note: `saves ${usd(((s.llm_cost_per_paper ?? 0) - (s.jev_cost_per_paper ?? 0)) * 1e6)}` }
		];
	});
</script>

<figure class="card px-5 pt-4 pb-4 sm:px-7" aria-label="Head-to-head results">
	<figcaption class="caption">
		<b>Table 1.</b>Head-to-head on the {#if s?.n}<span class="num">{int(s.n)}</span>{/if} papers both models judged, against the
		authors' own primary category. Best value in <strong class="font-semibold text-text">bold</strong>.
		{#if s?.n}They give the same answer on <span class="num">{pct(s.agreement)}</span> of papers.{/if}
	</figcaption>
	<div class="mt-3 overflow-x-auto">
		<table class="booktabs w-full min-w-[540px]">
			<thead>
				<tr class="text-left text-xs text-text-2">
					<th class="py-2 pr-4 font-medium">Metric</th>
					<th class="px-3 py-2 font-medium"><span class="inline-flex items-center gap-1.5"><span class="size-2 rounded-full bg-jev"></span>Jev</span></th>
					<th class="px-3 py-2 font-medium"><span class="inline-flex items-center gap-1.5"><span class="size-2 rounded-full bg-llm"></span>{llm}</span></th>
					<th class="py-2 pl-3 text-right font-medium">Difference</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as r (r.label)}
					<tr class="align-baseline">
						<td class="py-2.5 pr-4"><p class="text-sm font-medium">{r.label}</p><p class="text-xs text-muted">{r.hint}</p></td>
						{#each ['jev', 'llm'] as const as e (e)}
							<td class="num px-3 py-2.5 font-serif text-[1.35rem] leading-none tracking-tight {r.better === e ? 'font-bold text-text' : 'text-text-2'}">
								{e === 'jev' ? r.jev : r.llm}
							</td>
						{/each}
						<td class="num py-2.5 pl-3 text-right text-sm whitespace-nowrap text-text-2">
							{#if r.better}<span class="mr-1 inline-block size-1.5 rounded-full align-middle" style="background: var(--{r.better})"></span>{r.better === 'jev' ? 'Jev' : llm.replace('Claude ', '')} {r.note}{:else}tie{/if}
						</td>
					</tr>
				{:else}
					<tr><td colspan="4" class="py-8 text-center text-sm text-muted">Run <code class="font-mono">make benchmark N=200</code> to fill this table.</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
	{#if s?.n}
		<p class="num mt-2.5 text-xs text-muted">
			Spent so far: Jev {usd(s.jev_spent)} · {llm} {usd(s.llm_spent)}. Average input: {int(s.jev_tokens_in ?? 0)} tokens (Jev) vs {int(s.llm_tokens_in ?? 0)} prompt + {int(s.llm_tokens_out ?? 0)} output tokens ({llm}).
		</p>
	{/if}
</figure>
