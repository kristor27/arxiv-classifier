<script lang="ts">
	import { ago, ms, TOPICS, usd, VERDICTS } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import type { Edit } from '$lib/types';
	import ProbBar from './ProbBar.svelte';
	import VerdictBadge from './VerdictBadge.svelte';

	let { edit }: { edit: Edit } = $props();
	const j = $derived(edit.jev);
	const g = $derived(edit.llm);
	const color = $derived(VERDICTS[j.verdict].color);
	const clip = (s: string, n = 220) => (s.length > n ? s.slice(0, n) + '…' : s);
</script>

<article class="card relative overflow-hidden p-4 pl-5">
	<div class="absolute inset-y-0 left-0 w-1" style="background: {color}"></div>

	<header class="flex items-start justify-between gap-3">
		<div class="min-w-0">
			<a href={edit.url} target="_blank" rel="noopener"
				class="block truncate font-semibold hover:underline">{edit.title}</a>
			<p class="mt-0.5 truncate text-xs text-muted">
				{#if edit.anonymous}<span class="mr-1 rounded bg-surface-2 px-1.5 py-px text-text-2">anonymous</span>{/if}
				{edit.editor} · {ago(edit.created_at, live.now)}
				<span class="num {edit.byte_delta < 0 ? 'text-crit' : 'text-good'}">· {edit.byte_delta > 0 ? '+' : ''}{edit.byte_delta} B</span>
				{#if edit.comment}· “{clip(edit.comment, 60)}”{/if}
			</p>
		</div>
		<VerdictBadge verdict={j.verdict} />
	</header>

	{#if edit.removed || edit.added}
		<div class="mt-3 space-y-1 rounded-lg bg-surface-2 p-2.5 font-mono text-[11.5px] leading-relaxed">
			{#if edit.removed}<p class="break-words text-text-2"><span class="mr-1.5 select-none text-crit">−</span><span class="line-through decoration-crit/60">{clip(edit.removed)}</span></p>{/if}
			{#if edit.added}<p class="break-words text-text"><span class="mr-1.5 select-none text-good">+</span>{clip(edit.added)}</p>{/if}
		</div>
	{/if}

	<footer class="mt-3 grid gap-2">
		{#if j.probabilities}<ProbBar probs={j.probabilities} />{/if}
		<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted">
			<span class="inline-flex items-center gap-1 font-medium text-text-2">
				<span class="size-2 rounded-full bg-jev"></span> Jev
				<span class="num">{Math.round((j.confidence ?? 0) * 100)}% sure</span>
			</span>
			<span class="num">⚡ {ms(j.ms)}</span>
			<span class="num">{usd(j.cost)}</span>
			{#if j.topic}<span class="rounded bg-surface-2 px-1.5 py-px text-text-2">{TOPICS[j.topic] ?? j.topic}</span>{/if}
			<span>{j.kind}</span>
			<span>severity <span class="num">{j.severity.toFixed(1)}</span>/3</span>
			{#if g}
				<span class="ml-auto inline-flex items-center gap-1.5 rounded-full bg-surface-2 px-2 py-0.5">
					<span class="size-2 rounded-full bg-llm"></span>
					{g.label ?? g.model}: {VERDICTS[g.verdict].label.toLowerCase()} · <span class="num">{ms(g.ms)}</span> · <span class="num">{usd(g.cost)}</span>
					<span class={g.verdict === j.verdict ? 'text-good' : 'text-warn'}>{g.verdict === j.verdict ? '✓ agrees' : '≠ differs'}</span>
				</span>
			{/if}
			{#if edit.reverted}<span class="rounded-full bg-crit/15 px-2 py-0.5 font-medium text-crit">reverted by Wikipedia</span>{/if}
		</div>
	</footer>
</article>
