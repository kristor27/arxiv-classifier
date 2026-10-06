<script lang="ts">
	import { ago, CATEGORY_NAMES, ms, usd } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import type { Judgement, Paper } from '$lib/types';

	// One entry of an arXiv-style listing. The two verdicts sit in the margin, like a referee's notes.
	let { paper }: { paper: Paper } = $props();
	let open = $state(false);
	const truth = $derived(paper.primary_category);
	const top3 = (j: Judgement) =>
		Object.entries(j.probabilities ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 3).filter(([, p]) => p >= 0.01);
</script>

{#snippet note(j: Judgement, color: string)}
	{@const ok = j.category === truth}
	{@const lenient = !ok && paper.categories.includes(j.category)}
	<div class="grid gap-1 py-2 first:pt-0 last:pb-0">
		<div class="flex items-center gap-2 text-xs">
			<span class="size-2 shrink-0 rounded-full" style="background: {color}"></span>
			<span class="truncate font-medium text-text-2">{j.label}</span>
			<span class="num ml-auto text-muted">{ms(j.ms)}</span>
		</div>
		<div class="flex items-baseline gap-2">
			<span class="font-mono text-sm font-semibold {ok ? 'text-good' : lenient ? 'text-warn' : 'text-crit'}"
				title={ok ? 'Matches the primary category' : lenient ? 'Not the primary category, but one the authors cross-listed' : 'Wrong category'}>
				{ok ? '✓' : lenient ? '≈' : '✕'} {j.category}
			</span>
			<span class="num ml-auto text-xs text-muted">{usd(j.cost)}</span>
		</div>
		<p class="num truncate text-[11px] text-muted">
			{#if j.probabilities}
				{#each top3(j) as [c, p], i (c)}{i ? ' · ' : ''}<span class={i === 0 ? 'text-text-2' : ''}>{c} {Math.round(p * 100)}%</span>{/each}
			{:else}
				"{Math.round(j.confidence * 100)}% sure", self-reported
			{/if}
		</p>
	</div>
{/snippet}

<article class="card grid gap-x-6 gap-y-3 p-4 sm:p-5 md:grid-cols-[minmax(0,1fr)_14.5rem]">
	<div class="min-w-0">
		<p class="flex flex-wrap items-baseline gap-x-2 font-mono text-xs">
			<a href={paper.url} target="_blank" rel="noopener" class="text-text-2 hover:text-jev hover:underline">arXiv:{paper.id}</a>
			<span class="font-semibold text-text" title="The category the authors chose: the right answer">[{truth}]</span>
			{#each paper.categories.filter((c) => c !== truth).slice(0, 3) as c (c)}<span class="text-muted">{c}</span>{/each}
			<span class="ml-auto font-sans text-muted">{CATEGORY_NAMES[truth]} · {paper.jev.paper_type} · {ago(paper.published, live.now)}</span>
		</p>
		<h3 class="mt-1.5 font-serif text-[1.13rem] leading-snug font-medium text-balance">
			<a href={paper.url} target="_blank" rel="noopener" class="hover:underline">{paper.title}</a>
		</h3>
		<p class="mt-1 truncate text-xs text-text-2">{paper.authors}</p>
		<button type="button" onclick={() => (open = !open)} aria-expanded={open}
			class="mt-2 w-full cursor-pointer text-left font-serif text-[0.92rem] leading-relaxed text-text-2 {open ? '' : 'line-clamp-2'}">
			<span class="mr-1.5 font-sans text-[11px] font-semibold tracking-wide text-muted uppercase">Abstract</span>{paper.abstract}
		</button>
	</div>
	<aside class="divide-y divide-border border-t border-border pt-3 md:border-t-0 md:border-l md:pt-0 md:pl-5" aria-label="Verdicts">
		{@render note(paper.jev, 'var(--jev)')}
		{#if paper.llm}{@render note(paper.llm, 'var(--llm)')}{/if}
	</aside>
</article>
