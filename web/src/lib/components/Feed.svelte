<script lang="ts">
	import { CATEGORY_NAMES } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import type { Only } from '$lib/types';
	import PaperCard from './PaperCard.svelte';

	const llmName = $derived(live.stats?.engines.llm ?? 'LLM');
	const views = $derived<{ key: Only | null; label: string }[]>([
		{ key: null, label: 'All' },
		{ key: 'jev_wrong', label: 'Jev wrong' },
		{ key: 'llm_wrong', label: `${llmName.replace('Claude ', '')} wrong` },
		{ key: 'disagree', label: 'They disagree' }
	]);
	const counts = $derived(Object.fromEntries((live.stats?.per_category ?? []).map((c) => [c.category, c.n])));
	const chip = 'shrink-0 rounded-full border px-2.5 py-1 text-xs transition';
</script>

<section class="flex min-h-0 flex-col">
	<div class="mb-3 flex flex-wrap items-center gap-2">
		<div class="mr-auto flex gap-4 border-b border-border text-sm" role="tablist">
			{#each views as v (v.key)}
				<button role="tab" aria-selected={live.filter.only === v.key} onclick={() => live.setFilter({ only: v.key })}
					class="-mb-px border-b-2 pb-1.5 transition {live.filter.only === v.key ? 'border-text font-medium text-text' : 'border-transparent text-muted hover:text-text'}">{v.label}</button>
			{/each}
		</div>
		<button onclick={() => live.toggleFreeze()} title="Freeze the list while you read; papers are still judged"
			class="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium hover:border-muted">
			{live.frozen ? `▶ Unfreeze${live.queued.length ? ` (${live.queued.length} new)` : ''}` : '❚❚ Freeze'}
		</button>
	</div>

	<div class="mb-3 flex gap-1.5 overflow-x-auto pb-1" role="tablist" aria-label="Filter by the paper's true category">
		<button role="tab" aria-selected={!live.filter.category} onclick={() => live.setFilter({ category: null })}
			class="{chip} {!live.filter.category ? 'border-text bg-text text-surface' : 'border-border text-text-2 hover:border-muted'}">All</button>
		{#each Object.keys(CATEGORY_NAMES) as c (c)}
			<button role="tab" aria-selected={live.filter.category === c} onclick={() => live.setFilter({ category: c })} title={CATEGORY_NAMES[c]}
				class="{chip} font-mono {live.filter.category === c ? 'border-text bg-text text-surface' : 'border-border text-text-2 hover:border-muted'}">
				{c}<span class="num ml-1 font-sans text-muted">{counts[c] ?? 0}</span>
			</button>
		{/each}
	</div>

	<div class="grid gap-3">
		{#each live.papers as paper (paper.id)}
			<div class="enter"><PaperCard {paper} /></div>
		{:else}
			<p class="card p-8 text-center font-serif text-text-2">
				No papers yet. Run <code class="font-mono">make benchmark N=200</code> to race both models on the latest arXiv papers.
			</p>
		{/each}
	</div>
</section>

<style>
	.enter { animation: enter 0.45s cubic-bezier(0.2, 0.8, 0.2, 1); }
	@keyframes enter {
		from { opacity: 0; transform: translateY(-10px) scale(0.99); }
	}
</style>
