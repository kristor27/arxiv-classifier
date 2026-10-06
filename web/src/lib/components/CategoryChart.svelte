<script lang="ts">
	import { CATEGORY_NAMES, pct } from '$lib/format';
	import { live } from '$lib/live.svelte';

	// Accuracy per true category as a dumbbell: one dot per model on the same 0–100% scale.
	const rows = $derived(live.stats?.per_category ?? []);
	const llm = $derived(live.stats?.engines.llm ?? 'LLM');
	let hover = $state<string | null>(null);
</script>

<figure class="card p-5">
	<figcaption class="caption"><b>Figure 2.</b>Accuracy by true category. Each row puts both models on the same 0–100% scale; the number on the right is how many papers.</figcaption>
	<ul class="mt-3 flex gap-3 text-[11px] text-text-2">
		<li class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-jev"></span>Jev</li>
		<li class="flex items-center gap-1.5"><span class="size-2 rounded-full bg-llm"></span>{llm}</li>
	</ul>
	<div class="mt-3 grid gap-1.5">
		{#each rows as r (r.category)}
			<div class="grid grid-cols-[4.5rem_minmax(0,1fr)_2rem] items-center gap-2 text-xs" role="presentation"
				onmouseenter={() => (hover = r.category)} onmouseleave={() => (hover = null)}>
				<span class="font-mono text-text-2" title={CATEGORY_NAMES[r.category]}>{r.category}</span>
				<div class="relative h-5">
					<div class="absolute inset-x-0 top-1/2 h-px bg-border"></div>
					<div class="absolute top-1/2 h-[2px] -translate-y-1/2 bg-muted/50"
						style="left: {Math.min(r.jev, r.llm) * 100}%; width: {Math.abs(r.jev - r.llm) * 100}%"></div>
					<span class="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-llm ring-2 ring-surface" style="left: {r.llm * 100}%"></span>
					<span class="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-jev ring-2 ring-surface" style="left: {r.jev * 100}%"></span>
				</div>
				<span class="num text-right text-muted">{r.n}</span>
			</div>
		{:else}
			<p class="text-xs text-muted">No papers yet.</p>
		{/each}
	</div>
	{#if rows.length}
		<div class="mt-1 ml-[5rem] mr-[2.5rem] flex justify-between text-[10px] text-muted"><span>0%</span><span>50%</span><span>100%</span></div>
	{/if}
	<p class="num mt-2 h-4 text-[11px] text-text-2">
		{#if hover}
			{@const r = rows.find((x) => x.category === hover)!}
			{hover} {CATEGORY_NAMES[hover]}: Jev {pct(r.jev)} · {llm} {pct(r.llm)} on {r.n} papers
		{/if}
	</p>
</figure>
